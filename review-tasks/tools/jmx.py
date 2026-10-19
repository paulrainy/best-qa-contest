"""Элементы плана JMeter 5.6.3 и запись .jmx.

Сценарии задания 1г описываются на Python через фабрики этого модуля, а `render` пишет XML ровно так,
как его сохраняет JMeter 5.6.3. Имена и вид свойств сняты с JMeter (`check_jmx.groovy --sample`),
проверяются проходом через GUI-классы в `check_jmx.groovy`.
"""
from dataclasses import dataclass, field
from xml.sax.saxutils import escape, quoteattr

INDENT = '  '
FORBIDDEN = ('→', '`')


# ---------- свойства ----------

@dataclass
class S:
    name: str
    value: str


@dataclass
class B:
    name: str
    value: bool


@dataclass
class I:
    name: str
    value: int


@dataclass
class L:
    name: str
    value: int


@dataclass
class D:
    name: str
    value: float


@dataclass
class E:
    name: str
    element_type: str
    props: list
    gui: str | None = None
    test_class: str | None = None
    testname: str | None = None


@dataclass
class C:
    name: str
    items: list


@dataclass
class Raw:
    xml: str  # готовый XML, отступ — от уровня свойства


def num(name: str, value) -> object:
    """Число — intProp, строка (например, ${__P(threads,42)}) — stringProp, как пишет GUI."""
    return I(name, value) if isinstance(value, int) else S(name, str(value))


def java_hash(text: str) -> int:
    """String.hashCode() из Java: так JMeter называет строки в списке шаблонов Response Assertion."""
    data, h = text.encode('utf-16-be'), 0
    for i in range(0, len(data), 2):
        h = (31 * h + (data[i] << 8 | data[i + 1])) & 0xFFFFFFFF
    return h - (1 << 32) if h & 0x80000000 else h


def prop_xml(prop, depth: int) -> list[str]:
    pad = INDENT * depth
    if isinstance(prop, S):
        return [f'{pad}<stringProp name={quoteattr(prop.name)}>{escape(prop.value)}</stringProp>']
    if isinstance(prop, B):
        return [f'{pad}<boolProp name={quoteattr(prop.name)}>{str(prop.value).lower()}</boolProp>']
    if isinstance(prop, I):
        return [f'{pad}<intProp name={quoteattr(prop.name)}>{prop.value}</intProp>']
    if isinstance(prop, L):
        return [f'{pad}<longProp name={quoteattr(prop.name)}>{prop.value}</longProp>']
    if isinstance(prop, D):
        inner = INDENT * (depth + 1)
        return [f'{pad}<doubleProp>', f'{inner}<name>{escape(prop.name)}</name>',
                f'{inner}<value>{float(prop.value)}</value>', f'{inner}<savedValue>0.0</savedValue>',
                f'{pad}</doubleProp>']
    if isinstance(prop, C):
        if not prop.items:
            return [f'{pad}<collectionProp name={quoteattr(prop.name)}/>']
        lines = [f'{pad}<collectionProp name={quoteattr(prop.name)}>']
        for item in prop.items:
            lines += prop_xml(item, depth + 1)
        return lines + [f'{pad}</collectionProp>']
    if isinstance(prop, E):
        attrs = f'name={quoteattr(prop.name)} elementType={quoteattr(prop.element_type)}'
        if prop.gui:
            attrs += f' guiclass={quoteattr(prop.gui)} testclass={quoteattr(prop.test_class)}'
            attrs += f' testname={quoteattr(prop.testname)}'
        if not prop.props:
            return [f'{pad}<elementProp {attrs}/>']
        lines = [f'{pad}<elementProp {attrs}>']
        for item in prop.props:
            lines += prop_xml(item, depth + 1)
        return lines + [f'{pad}</elementProp>']
    if isinstance(prop, Raw):
        return [pad + line for line in prop.xml.strip('\n').splitlines()]
    raise TypeError(prop)


# ---------- элемент и запись ----------

@dataclass
class El:
    tag: str
    gui: str
    test_class: str
    name: str
    props: list = field(default_factory=list)
    children: list = field(default_factory=list)
    enabled: bool = True
    comment: str = ''

    def prop(self, name: str):
        """Значение свойства верхнего уровня по имени — для --show и тестов."""
        for p in self.props:
            if getattr(p, 'name', None) == name:
                return p.value if hasattr(p, 'value') else p
        return None


def check_names(element: El, where: str = 'Test Plan'):
    seen = set()
    for child in element.children:
        if any(ch in child.name for ch in FORBIDDEN):
            raise ValueError(f'недопустимый символ в имени «{child.name}»')
        if child.name in seen:
            raise ValueError(f'повтор имени «{child.name}» в «{where}»')
        seen.add(child.name)
        check_names(child, child.name)


def element_xml(element: El, depth: int) -> list[str]:
    pad = INDENT * depth
    attrs = (f'guiclass={quoteattr(element.gui)} testclass={quoteattr(element.test_class)} '
             f'testname={quoteattr(element.name)}')
    if not element.enabled:
        attrs += ' enabled="false"'
    props = list(element.props)
    if element.comment:
        props.append(S('TestPlan.comments', element.comment))
    if props:
        lines = [f'{pad}<{element.tag} {attrs}>']
        for prop in props:
            lines += prop_xml(prop, depth + 1)
        lines.append(f'{pad}</{element.tag}>')
    else:
        lines = [f'{pad}<{element.tag} {attrs}/>']
    if element.children:
        lines.append(f'{pad}<hashTree>')
        for child in element.children:
            lines += element_xml(child, depth + 1)
        lines.append(f'{pad}</hashTree>')
    else:
        lines.append(f'{pad}<hashTree/>')
    return lines


def render(root: El) -> str:
    check_names(root)
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<jmeterTestPlan version="1.2" properties="5.0" jmeter="5.6.3">',
             f'{INDENT}<hashTree>']
    lines += element_xml(root, 2)
    lines += [f'{INDENT}</hashTree>', '</jmeterTestPlan>']
    return '\n'.join(lines) + '\n'


def paths(root: El) -> dict:
    """Путь в дереве («Thread Group → Вход → POST /auth/login») → элемент. Корень — «Test Plan»."""
    check_names(root)
    found = {'Test Plan': root}

    def walk(element: El, prefix: str):
        for child in element.children:
            path = f'{prefix} → {child.name}' if prefix else child.name
            found[path] = child
            walk(child, path)

    walk(root, '')
    return found


# ---------- фабрики ----------

def _el(tag, gui, test_class, name, props, children=(), enabled=True, comment=''):
    return El(tag, gui, test_class, name, list(props), list(children), enabled, comment)


def _bean(test_class, name, props, children=(), enabled=True, comment=''):
    return _el(test_class, 'TestBeanGUI', test_class, name, props, children, enabled, comment)


def _arguments(name: str, variables: dict, gui='ArgumentsPanel', testname='User Defined Variables') -> E:
    items = [E(key, 'Argument', [S('Argument.name', key), S('Argument.value', str(value)),
                                 S('Argument.metadata', '=')])
             for key, value in variables.items()]
    return E(name, 'Arguments', [C('Arguments.arguments', items)], gui, 'Arguments', testname)


def test_plan(name, children=(), variables=None, comment=''):
    return _el('TestPlan', 'TestPlanGui', 'TestPlan', name,
               [_arguments('TestPlan.user_defined_variables', variables or {})], children, comment=comment)


def thread_group(name, threads, rampup, duration=None, children=(), on_error='continue', loops=-1,
                 same_user=True, enabled=True, comment=''):
    props = [S('ThreadGroup.on_sample_error', on_error), num('ThreadGroup.num_threads', threads),
             num('ThreadGroup.ramp_time', rampup), B('ThreadGroup.same_user_on_next_iteration', same_user),
             E('ThreadGroup.main_controller', 'LoopController',
               [num('LoopController.loops', loops), B('LoopController.continue_forever', False)],
               'LoopControlPanel', 'LoopController', 'Loop Controller')]
    if duration is not None:
        props += [B('ThreadGroup.scheduler', True), S('ThreadGroup.duration', str(duration))]
    return _el('ThreadGroup', 'ThreadGroupGui', 'ThreadGroup', name, props, children, enabled, comment)


def _http_common(domain, port, protocol, connect_timeout, response_timeout, content_encoding):
    props = []
    if domain is not None:
        props.append(S('HTTPSampler.domain', domain))
    if port is not None:
        props.append(num('HTTPSampler.port', port))
    if protocol is not None:
        props.append(S('HTTPSampler.protocol', protocol))
    if connect_timeout is not None:
        props.append(S('HTTPSampler.connect_timeout', str(connect_timeout)))
    if response_timeout is not None:
        props.append(S('HTTPSampler.response_timeout', str(response_timeout)))
    if content_encoding is not None:
        props.append(S('HTTPSampler.contentEncoding', content_encoding))
    return props


def http_defaults(name, domain=None, port=None, protocol=None, connect_timeout=None, response_timeout=None,
                  content_encoding=None, embedded=False, enabled=True, comment=''):
    props = [E('HTTPsampler.Arguments', 'Arguments', [C('Arguments.arguments', [])],
               'HTTPArgumentsPanel', 'Arguments', 'User Defined Variables'),
             S('HTTPSampler.implementation', 'HttpClient4')]
    props += _http_common(domain, port, protocol, connect_timeout, response_timeout, content_encoding)
    if embedded:
        props.append(B('HTTPSampler.image_parser', True))
    return _el('ConfigTestElement', 'HttpDefaultsGui', 'ConfigTestElement', name, props, enabled=enabled,
               comment=comment)


def http_request(name, method, path, body=None, params=(), keep_alive=True, embedded=False,
                 connect_timeout=None, response_timeout=None, domain=None, port=None, protocol=None,
                 follow_redirects=True, content_encoding=None, children=(), enabled=True, comment=''):
    if body is not None:
        items = [E('', 'HTTPArgument', [B('HTTPArgument.always_encode', False), S('Argument.value', body),
                                        S('Argument.metadata', '=')])]
    else:
        items = [E(key, 'HTTPArgument', [B('HTTPArgument.always_encode', True), S('Argument.name', key),
                                         S('Argument.value', str(value)), S('Argument.metadata', '=')])
                 for key, value in params]
    props = [E('HTTPsampler.Arguments', 'Arguments', [C('Arguments.arguments', items)],
               'HTTPArgumentsPanel', 'Arguments', 'User Defined Variables'),
             S('HTTPSampler.method', method), B('HTTPSampler.follow_redirects', follow_redirects),
             B('HTTPSampler.use_keepalive', keep_alive), B('HTTPSampler.postBodyRaw', body is not None),
             S('HTTPSampler.path', path)]
    props += _http_common(domain, port, protocol, connect_timeout, response_timeout, content_encoding)
    if embedded:
        props.append(B('HTTPSampler.image_parser', True))
    return _el('HTTPSamplerProxy', 'HttpTestSampleGui', 'HTTPSamplerProxy', name, props, children, enabled,
               comment)


def header_manager(name, headers, enabled=True, comment=''):
    items = [E(key, 'Header', [S('Header.name', key), S('Header.value', value)]) for key, value in headers]
    return _el('HeaderManager', 'HeaderPanel', 'HeaderManager', name, [C('HeaderManager.headers', items)],
               enabled=enabled, comment=comment)


def cookie_manager(name, clear_each_iteration=False, enabled=True, comment=''):
    return _el('CookieManager', 'CookiePanel', 'CookieManager', name,
               [C('CookieManager.cookies', []), B('CookieManager.clearEachIteration', clear_each_iteration),
                B('CookieManager.controlledByThreadGroup', False)], enabled=enabled, comment=comment)


def user_variables(name, variables: dict, enabled=True, comment=''):
    arguments = _arguments('', variables)
    return _el('Arguments', 'ArgumentsPanel', 'Arguments', name, arguments.props, enabled=enabled, comment=comment)


def csv_data_set(name, filename, variable_names='', ignore_first_line=False, delimiter=',', recycle=True,
                 stop_thread=False, share_mode='shareMode.all', encoding='UTF-8', quoted=False,
                 enabled=True, comment=''):
    return _bean('CSVDataSet', name, [
        S('delimiter', delimiter), S('fileEncoding', encoding), S('filename', filename),
        B('ignoreFirstLine', ignore_first_line), B('quotedData', quoted), B('recycle', recycle),
        S('shareMode', share_mode), B('stopThread', stop_thread), S('variableNames', variable_names),
    ], enabled=enabled, comment=comment)


def transaction(name, children=(), parent=True, include_timers=False, enabled=True, comment=''):
    return _el('TransactionController', 'TransactionControllerGui', 'TransactionController', name,
               [B('TransactionController.includeTimers', include_timers), B('TransactionController.parent', parent)],
               children, enabled, comment)


def once_only(name, children=(), enabled=True, comment=''):
    return _el('OnceOnlyController', 'OnceOnlyControllerGui', 'OnceOnlyController', name, [], children,
               enabled, comment)


def if_controller(name, condition, children=(), use_expression=True, evaluate_all=False, enabled=True,
                  comment=''):
    return _el('IfController', 'IfControllerPanel', 'IfController', name,
               [S('IfController.condition', condition), B('IfController.evaluateAll', evaluate_all),
                B('IfController.useExpression', use_expression)], children, enabled, comment)


def loop_controller(name, loops, children=(), enabled=True, comment=''):
    return _el('LoopController', 'LoopControlPanel', 'LoopController', name,
               [num('LoopController.loops', loops)], children, enabled, comment)


def flow_control_action(name, children=(), action=1, target=0, duration='0', enabled=True, comment=''):
    """action 1 — Pause; длительность паузы обычно задаёт дочерний таймер."""
    return _el('TestAction', 'TestActionGui', 'TestAction', name,
               [I('ActionProcessor.action', action), I('ActionProcessor.target', target),
                S('ActionProcessor.duration', str(duration))], children, enabled, comment)


def _scope(scope):
    return [] if scope is None else [S('Sample.scope', scope)]


def json_extractor(name, var, expr, default=None, match_no='1', scope=None, enabled=True, comment=''):
    props = [S('JSONPostProcessor.referenceNames', var), S('JSONPostProcessor.jsonPathExprs', expr),
             S('JSONPostProcessor.match_numbers', str(match_no))]
    if default is not None:
        props.append(S('JSONPostProcessor.defaultValues', default))
    return _el('JSONPostProcessor', 'JSONPostProcessorGui', 'JSONPostProcessor', name,
               _scope(scope) + props, enabled=enabled, comment=comment)


def regex_extractor(name, var, regex, template='$1$', default='', match_no='1', field='false',
                    default_empty=False, scope=None, enabled=True, comment=''):
    """field: 'false' — тело ответа, 'true' — заголовки ответа, 'unescaped', 'as_document', 'URL', 'code'…"""
    return _el('RegexExtractor', 'RegexExtractorGui', 'RegexExtractor', name, _scope(scope) + [
        S('RegexExtractor.useHeaders', field), S('RegexExtractor.refname', var), S('RegexExtractor.regex', regex),
        S('RegexExtractor.template', template), S('RegexExtractor.default', default),
        B('RegexExtractor.default_empty_value', default_empty), S('RegexExtractor.match_number', str(match_no)),
    ], enabled=enabled, comment=comment)


CONTAINS, MATCHES, EQUALS, SUBSTRING, NOT, OR = 2, 1, 8, 16, 4, 32
RESPONSE_DATA, RESPONSE_CODE = 'Assertion.response_data', 'Assertion.response_code'


def response_assertion(name, patterns, field=RESPONSE_DATA, test_type=SUBSTRING, assume_success=False,
                       custom_message='', scope=None, enabled=True, comment=''):
    items = [S(str(java_hash(p)), p) for p in patterns]
    return _el('ResponseAssertion', 'AssertionGui', 'ResponseAssertion', name, _scope(scope) + [
        C('Asserion.test_strings', items), S('Assertion.custom_message', custom_message),
        S('Assertion.test_field', field), B('Assertion.assume_success', assume_success),
        I('Assertion.test_type', test_type),
    ], enabled=enabled, comment=comment)


def json_assertion(name, path, expected='', validate=True, expect_null=False, invert=False, regex=False,
                   enabled=True, comment=''):
    return _el('JSONPathAssertion', 'JSONPathAssertionGui', 'JSONPathAssertion', name, [
        S('JSON_PATH', path), S('EXPECTED_VALUE', expected), B('JSONVALIDATION', validate),
        B('EXPECT_NULL', expect_null), B('INVERT', invert), B('ISREGEX', regex),
    ], enabled=enabled, comment=comment)


def duration_assertion(name, ms, enabled=True, comment=''):
    return _el('DurationAssertion', 'DurationAssertionGui', 'DurationAssertion', name,
               [S('DurationAssertion.duration', str(ms))], enabled=enabled, comment=comment)


def constant_timer(name, delay, enabled=True, comment=''):
    return _el('ConstantTimer', 'ConstantTimerGui', 'ConstantTimer', name,
               [S('ConstantTimer.delay', str(delay))], enabled=enabled, comment=comment)


def uniform_random_timer(name, delay, range_, enabled=True, comment=''):
    return _el('UniformRandomTimer', 'UniformRandomTimerGui', 'UniformRandomTimer', name,
               [S('ConstantTimer.delay', str(delay)), S('RandomTimer.range', str(range_))],
               enabled=enabled, comment=comment)


def constant_throughput_timer(name, per_minute, calc_mode=0, enabled=True, comment=''):
    """calc_mode 0 — this thread only, 1 — all active threads, 2 — all active threads in current thread group."""
    return _bean('ConstantThroughputTimer', name, [I('calcMode', calc_mode), D('throughput', per_minute)],
                 enabled=enabled, comment=comment)


def precise_throughput_timer(name, throughput, period=3600, duration=3600, enabled=True, comment=''):
    """throughput событий за period секунд."""
    duration_prop = L('duration', duration) if isinstance(duration, int) else S('duration', str(duration))
    return _bean('PreciseThroughputTimer', name, [
        D('allowedThroughputSurplus', 1.0), I('batchSize', 1), I('batchThreadDelay', 0), duration_prop,
        I('exactLimit', 10000), L('randomSeed', 0), D('throughput', throughput), I('throughputPeriod', period),
    ], enabled=enabled, comment=comment)


JSR223 = {'sampler': 'JSR223Sampler', 'pre': 'JSR223PreProcessor', 'post': 'JSR223PostProcessor',
          'timer': 'JSR223Timer', 'assertion': 'JSR223Assertion'}


def jsr223(kind, name, script, cache=True, language='groovy', parameters='', enabled=True, comment=''):
    return _bean(JSR223[kind], name, [
        S('cacheKey', str(cache).lower()), S('filename', ''), S('parameters', parameters), S('script', script),
        S('scriptLanguage', language),
    ], enabled=enabled, comment=comment)


def beanshell_pre(name, script, enabled=True, comment=''):
    return _bean('BeanShellPreProcessor', name, [
        S('filename', ''), S('parameters', ''), B('resetInterpreter', False), S('script', script),
    ], enabled=enabled, comment=comment)


def debug_sampler(name, enabled=True, comment=''):
    return _bean('DebugSampler', name, [
        B('displayJMeterProperties', False), B('displayJMeterVariables', True), B('displaySystemProperties', False),
    ], enabled=enabled, comment=comment)


def jdbc_config(name, pool, url, user, password, pool_max, driver='org.postgresql.Driver', timeout=10000,
                autocommit=True, check_query='', enabled=True, comment=''):
    return _bean('JDBCDataSource', name, [
        B('autocommit', autocommit), S('checkQuery', check_query), S('connectionAge', '5000'),
        S('connectionProperties', ''), S('dataSource', pool), S('dbUrl', url), S('driver', driver),
        S('initQuery', ''), B('keepAlive', True), S('password', password), S('poolMax', str(pool_max)),
        B('preinit', False), S('timeout', str(timeout)), S('transactionIsolation', 'DEFAULT'),
        S('trimInterval', '60000'), S('username', user),
    ], enabled=enabled, comment=comment)


def jdbc_request(name, pool, query, query_type='Prepared Select Statement', args='', types='',
                 result_var='', variable_names='', timeout='', children=(), enabled=True, comment=''):
    return _bean('JDBCSampler', name, [
        S('dataSource', pool), S('query', query), S('queryArguments', args), S('queryArgumentsTypes', types),
        S('queryTimeout', str(timeout)), S('queryType', query_type), S('resultSetHandler', 'Store as String'),
        S('resultSetMaxRows', ''), S('resultVariable', result_var), S('variableNames', variable_names),
    ], children, enabled, comment)


SAVE_CONFIG = '''
<objProp>
  <name>saveConfig</name>
  <value class="SampleSaveConfiguration">
    <time>true</time>
    <latency>true</latency>
    <timestamp>true</timestamp>
    <success>true</success>
    <label>true</label>
    <code>true</code>
    <message>true</message>
    <threadName>true</threadName>
    <dataType>true</dataType>
    <encoding>false</encoding>
    <assertions>true</assertions>
    <subresults>true</subresults>
    <responseData>false</responseData>
    <samplerData>false</samplerData>
    <xml>false</xml>
    <fieldNames>true</fieldNames>
    <responseHeaders>false</responseHeaders>
    <requestHeaders>false</requestHeaders>
    <responseDataOnError>false</responseDataOnError>
    <saveAssertionResultsFailureMessage>true</saveAssertionResultsFailureMessage>
    <assertionsResultsToSave>0</assertionsResultsToSave>
    <bytes>true</bytes>
    <sentBytes>true</sentBytes>
    <url>true</url>
    <threadCounts>true</threadCounts>
    <idleTime>true</idleTime>
    <connectTime>true</connectTime>
  </value>
</objProp>
'''


def _collector(gui, name, filename, enabled, comment):
    return _el('ResultCollector', gui, 'ResultCollector', name, [
        B('ResultCollector.error_logging', False), Raw(SAVE_CONFIG), S('filename', filename),
    ], enabled=enabled, comment=comment)


def view_results_tree(name, filename='', enabled=True, comment=''):
    return _collector('ViewResultsFullVisualizer', name, filename, enabled, comment)


def summary_report(name, filename='', enabled=True, comment=''):
    return _collector('SummaryReport', name, filename, enabled, comment)


def backend_listener_influx(name, url, application, measurement='jmeter', summary_only=False,
                            percentiles='90;95;99', samplers_regex='.*', test_title='Test name', event_tags='',
                            enabled=True, comment=''):
    variables = {
        'influxdbMetricsSender': 'org.apache.jmeter.visualizers.backend.influxdb.HttpMetricsSender',
        'influxdbUrl': url, 'application': application, 'measurement': measurement,
        'summaryOnly': str(summary_only).lower(), 'samplersRegex': samplers_regex, 'percentiles': percentiles,
        'testTitle': test_title, 'eventTags': event_tags,
    }
    return _el('BackendListener', 'BackendListenerGui', 'BackendListener', name, [
        _arguments('arguments', variables),
        S('classname', 'org.apache.jmeter.visualizers.backend.influxdb.InfluxdbBackendListenerClient'),
    ], enabled=enabled, comment=comment)

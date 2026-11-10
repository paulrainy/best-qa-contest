# Independent senior review and acceptance — Java first plan

Reviewed range: 5c62e822404721fbaeddbed9919ab9dd874e2e73..cfc140a1ced102097cae6e183ba876f975101f51. Root checkout was read-only throughout this review. Replay used acceptance-clone at cfc140a with core.autocrlf=true and real LFS binaries. No subagents. No push/merge. Scope: approved Java reference plus shared contract, stand fixes, distribution and common tools; the other three references are separate deliverables.

## Strengths

- F01–F18 trace to executable assertions, independent account/client preparation, decimal money comparisons and explicit status, event and database observations. The selected ordinary money check detects a deliberately broken product, demonstrated below.
- CommissionTest.java:17 and AsyncTest.java:41 attach known-cause markers only to the actual money assertions. HTTP preparation, timeout and SQL failures are not disguised as expected product defects. F16 preparation exhausts the free threshold before the failing transfer, isolating it from F10.
- support/GlobalStandScope.java:18 attempts restoration of both consumers and the clock even when an earlier restoration fails; try-with-resources covers assertion exits. SupportTest exercises missing-event and transfer timeouts, queue binding/deletion, and restoration after an exception against real resources.
- jury/tools/check_reference_results.py:9 checks the full exact inventory, duplicate/missing/extra tests, assertion types and targeted causes. The fresh-report cleanup prevents partial Maven runs from borrowing stale successful XML.
- Four physical participant distributions contain identical ready runtime files, with manifest and archive verification. The current source transaction boundaries, atomic balance updates, duplicate accounting guard, exact decimal credit and usage queries address the removed seeded errors without altering F10/F16/N1.

## Findings

Critical: none.

Important: none.

Minor: docs/superpowers/specs/2026-11-10-final-four-directions-design.md:3 still described implementation as not started at reviewed cfc140a. This conflicts with the delivered Java/common work and can confuse the next executor about approval status. Update acceptance metadata to identify Java/common preparation as approved/completed and the three remaining references as pending. Root acknowledged this as part of final acceptance metadata; no source change is required for this item.

## Independent replay

Environment: macOS arm64, Temurin JDK 17.0.21+9 and Homebrew JDK 21.0.13.0.3; common unit suite additionally run with CPython 3.11.14. The clone Maven cache was populated from scratch using the reference README, which correctly documents that initial reference dependency installation needs network access. Ready-stand offline replay/archive creation was performed separately by root and is not claimed as my independent execution.

Same distributed stand SHA-256 throughout: 73c7773c0c029702e781f3dfd3e625046e5e69866dd1def82f71c47511113ecf.

Commands: launch participant run.sh with JAVA_HOME for the chosen JVM; HTTP health and one reset; from final-task/1a-java/jury/reference run `mvn -B test`, invoke the shared checker over the resulting XML, then `mvn -B test -DexcludedGroups=known_issue`. Stop/restart the same JAR for Java 21. Results:

| Run | Tests | Failures | Errors | Skips | Exit/checker |
| --- | ---: | ---: | ---: | ---: | --- |
| Java17 full | 61 | 2 exact F10/F16 | 0 | 0 | Maven1 / checker0 |
| Java17 control | 59 | 0 | 0 | 0 | Maven0 |
| Java21 full | 61 | 2 exact F10/F16 | 0 | 0 | Maven1 / checker0 |
| Java21 control | 59 | 0 | 0 | 0 | Maven0 |
| Java21 unavailable JDBC port19499 full | 61 | 2 exact F10/F16 | 39 | 0 | Maven1 / checker1 |
| Java21 restored JDBC control | 59 | 0 | 0 | 0 | Maven0 |

The deliberate JDBC outage retained both known money assertions, yet the checker rejected actual connection errors with explicit testcase diagnostics. This directly demonstrates that a broken DB connection cannot be counted as the accepted two-defect result.

The 12 common result-checker unit tests and 10 distribution-verifier unit tests all passed on CPython3.11.14. Clone distribution verifier passed. Clone status remained clean.

## Controlled mutation and restoration

Only a separate reviewer/mutant source copy was changed: AccountingConsumer.java:111, `BigDecimal credited = amount;` -> `BigDecimal credited = amount.add(new BigDecimal("0.01"));`. All scratch sources were compiled with JDK17 `javac --release 17` against the clone ready runtime libraries and launched through stand.Main, HTTP18420/AMQP5692/H219420. Participant JARs were never changed.

Unchanged ordinary test command: `mvn -B test -Dtest=TransferTest#ownTransferCompletesWithExactBalances -Dapi.url=http://localhost:18420 -Ddb.url=jdbc:h2:tcp://localhost:19420/mem:stand`.

Mutation result: 1 test, 1 assertion failure, 0 errors, 0 skips; expected recipient balance1000100, actual1000100.01. Exact scratch source was then restored from the clean clone, recompiled and restarted; the same test passed. The affected test also passed against the original distributed JAR on the standard ports. Final healthy control passed59 tests after the independent DB-outage experiment. All reviewer stand processes have been stopped.

## Evidence

- replay-summary.json: XML-derived counts for all replay/mutation/control phases.
- java17-full/, java17-control/, java21-full/, java21-control/: fresh XML.
- replay-java17-checker.log and replay-java21-checker.log: accepted full-run inventories.
- mutation-failure/, mutation-restored/, original-after-mutation/: selected-test XML.
- mutation-test.log, mutation-restored-test.log, original-after-mutation-test.log: Maven execution evidence.
- db-unavailable/, db-unavailable-full.log, db-unavailable-checker.log: real infrastructure-error rejection.
- healthy-after-db-control/: final restored control XML.
- restoration.json: clean clone HEAD/status, unchanged stand SHA, restored scratch source equality.
- shared-tools-unit311.log and distribution.log: unit and distribution verification.

## Declined to judge

- Implementation/readiness of manual, load and Python references: explicitly excluded from the approved first Java deliverable and not represented as completed.
- Windows/VDI runtime acceptance: no target environment was available; the plan explicitly leaves a separate pilot before official distribution. macOS17/21 results do not establish VDI compatibility.

No assigned Java/common-preparation behavior was otherwise set aside as outside scope.

## Verdict

Ready for acceptance of the approved Java/common-preparation implementation: YES. No Critical or Important finding. Resolve the minor status metadata during acceptance closure. This is not authorization to push/merge and not a declaration of Windows/VDI readiness. The independent fresh-clone full/control replays, real JDBC-error rejection and controlled broken-product/restored-product test establish the intended Java acceptance result.

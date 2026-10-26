package stand;

/** Ошибка API с HTTP-статусом и кодом из ТЗ. */
final class ApiError extends RuntimeException {

    final int status;
    final String code;

    ApiError(int status, String code, String message) {
        super(message);
        this.status = status;
        this.code = code;
    }
}

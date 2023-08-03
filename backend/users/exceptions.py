from rest_framework import exceptions, status


class CustomDeleteError(exceptions.APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Ошибка при удалении объекта."
    default_code = "delete_error"

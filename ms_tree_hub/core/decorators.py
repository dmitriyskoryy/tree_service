import functools
import logging

from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response

logger = logging.getLogger('main_info')


def custom_exception_handler(fn):
    """Decorator for all view's methods, handle all missing exceptions to avoid 500 error"""

    @functools.wraps(fn)
    def inner(request, *args, **kwargs):
        try:
            return fn(request, *args, **kwargs)
        except Exception as exc:
            if isinstance(exc, APIException):
                return Response(exc.detail, status=exc.status_code)
            logger.error(f'unhandled exception; {exc}', exc_info=True)
            return Response({'error': 'Something went wrong, please contact the dev'},
                            status=status.HTTP_400_BAD_REQUEST)

    return inner

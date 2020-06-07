from rest_framework.exceptions import ErrorDetail
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = exception_handler(exc, context)

    if response is not None and 'detail' not in response.data:
        err = ''
        for k in exc.detail.keys():
            v = exc.detail[k]
            if isinstance(v, list):
                v = v[0]

            if isinstance(v, ErrorDetail):
                err = f'{k}, {v}'
            else:
                err = str(v)

            if err:
                break
        response.data['detail'] = err
    elif isinstance(response.data['detail'], list):
        response.data['detail'] = response.data['detail'][0]

    return response

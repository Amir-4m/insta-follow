from drf_yasg import openapi

DAILY_REWARD_DOCS_RESPONSE = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'page': openapi.Schema(
            type=openapi.TYPE_OBJECT,
            description='username of the page which got the reward'

        ),
        'amount': openapi.Schema(
            type=openapi.TYPE_INTEGER,
            description='amount of the coins that rewarded to the page.'
        ),
        'rewarded': openapi.Schema(
            type=openapi.TYPE_BOOLEAN,
            description='status of the reward operation. this is true if page gets the reward successfully'
        ),

    }
)

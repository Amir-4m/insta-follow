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

TAPSELL_REWARD_DOCS_RESPONSE = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'valid': openapi.Schema(
            type=openapi.TYPE_BOOLEAN,
            description='confirms that the user viewed the ad properly or not'

        )
    }
)

TAPSELL_REWARD_DOCS = openapi.Schema(
    required=['suggestion_id', 'event'],
    type=openapi.TYPE_OBJECT,
    properties={
        'event': openapi.Schema(
            type=openapi.TYPE_STRING,
            description='event of the user action on ad (click/view)'

        ),
        'suggestion_id': openapi.Schema(
            type=openapi.TYPE_STRING,
            description='id that the tapsell returns on ad view'
        ),

    }
)

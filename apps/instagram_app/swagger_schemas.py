from drf_yasg import openapi

ORDER_POST_DOCS = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=['action', 'target_no', 'link'],
    properties={
        'action': openapi.Schema(
            type=openapi.TYPE_STRING,
            description='requested action for the order i.e. "L" for Like',
        ),
        'target_no': openapi.Schema(
            type=openapi.TYPE_INTEGER,
            description='number of the action user need for order i.e. 20 likes for order'
        ),
        'link': openapi.Schema(
            type=openapi.TYPE_STRING,
            description='the post instagram url (not required if action is follow)'
        ),
        'instagram_username': openapi.Schema(
            type=openapi.TYPE_STRING,
            description='pass this parameter when the action is follow. it should be instagram username of the user'
        ),

    }
)
INQUIRY_POST_DOC = openapi.Schema(
    required=['page_id', 'done_ids'],
    type=openapi.TYPE_OBJECT,
    properties={
        'page_id': openapi.Schema(
            type=openapi.TYPE_INTEGER,
            description='id of the page user set as active',
        ),
        'done_ids': openapi.Schema(
            type=openapi.TYPE_ARRAY,
            description='a list of order ids that has been done by user action',
            items=openapi.Schema(type=openapi.TYPE_INTEGER)

        )
    }
)
PROFILE_POST_DOC = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    operation_description="Add an existed instagram page to user pages list",
    properties={
        'instagram_username': openapi.Schema(
            type=openapi.TYPE_STRING,
            description='instagram username of the page user want to add to his/her pages list',
        ),
        'user_id': openapi.Schema(
            type=openapi.TYPE_INTEGER,
            description='instagram user id of the page'
        ),
    }
)

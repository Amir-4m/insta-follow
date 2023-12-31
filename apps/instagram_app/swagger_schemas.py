from drf_yasg import openapi

ORDER_POST_DOCS = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=['action', 'target_no', 'entity_id'],
    properties={
        'action': openapi.Schema(
            type=openapi.TYPE_STRING,
            description='requested action for the order i.e. "L" for Like',
        ),
        'target_no': openapi.Schema(
            type=openapi.TYPE_INTEGER,
            description='number of the action user need for order i.e. 20 likes for order'
        ),
        'shortcode': openapi.Schema(
            type=openapi.TYPE_STRING,
            description='media shortcode (not required if action is follow)'
        ),
        'instagram_username': openapi.Schema(
            type=openapi.TYPE_STRING,
            description='pass this parameter when the action is follow. it should be instagram username of the user'
        ),
        'comments': openapi.Schema(
            type=openapi.TYPE_ARRAY,
            description='list of texts for comment orders. pass empty array to pass all pre-defined comments',
            items=openapi.Schema(type=openapi.TYPE_INTEGER)
        ),

    }
)
INQUIRY_POST_DOC = openapi.Schema(
    required=['done_ids'],
    type=openapi.TYPE_OBJECT,
    properties={
        'done_ids': openapi.Schema(
            type=openapi.TYPE_ARRAY,
            description='a list of order ids that has been done by user action',
            items=openapi.Schema(type=openapi.TYPE_INTEGER)

        )
    }
)

PackageOrder_DOC = openapi.Schema(
    required=['coin_package', 'price'],
    type=openapi.TYPE_OBJECT,
    properties={
        'coin_package': openapi.Schema(
            type=openapi.TYPE_OBJECT,
            description='ID of the chosen coin package',

        ),
        'price': openapi.Schema(
            type=openapi.TYPE_INTEGER,
            description='price of the package.'
        ),
    }
)
PackageOrder_DOCS_RESPONSE = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={

        'id': openapi.Schema(
            type=openapi.TYPE_INTEGER,
            description='id of the object'
        ),
        'invoice_number': openapi.Schema(
            type=openapi.TYPE_STRING,
            description='invoice_number of the object'
        ),
        'coin_package': openapi.Schema(
            type=openapi.TYPE_OBJECT,
            description='id of the selected coin package'
        ),
        'is_paid': openapi.Schema(
            type=openapi.TYPE_BOOLEAN,
            description='status of the order'
        ),
        'price': openapi.Schema(
            type=openapi.TYPE_INTEGER,
            description='price of the package'
        ),
        'package_detail': openapi.Schema(
            type=openapi.TYPE_OBJECT,
            description='detail of the package'
        ),
        'gateways': openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(type=openapi.TYPE_OBJECT),
            description='allowed gateways for order'
        ),
        'redirect_url': openapi.Schema(
            type=openapi.TYPE_STRING,
            description='redirect url after the payment is done'
        )
    }
)

PURCHASE_DOC = openapi.Schema(
    required=['gateway_code', 'package_order'],
    type=openapi.TYPE_OBJECT,
    properties={
        'package_order': openapi.Schema(
            type=openapi.TYPE_OBJECT,
            description='ID of the chosen package order',

        ),
        'gateway_code': openapi.Schema(
            type=openapi.TYPE_INTEGER,
            description='ID of the gateway which purchase is done by'
        ),
        'purchase_token': openapi.Schema(
            type=openapi.TYPE_STRING,
            description='purchase token that gives back from purchasing stage (only required for gateway bazaar)'
        ),
    }
)
PURCHASE_DOCS_RESPONSE = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={

        'purcahse_verified': openapi.Schema(
            type=openapi.TYPE_BOOLEAN,
            description='status of the purchase'
        ),

    }
)
TRANSFER_COIN_DOC = openapi.Schema(
    required=['to_page', 'amount'],
    type=openapi.TYPE_OBJECT,
    properties={
        'to_page': openapi.Schema(
            type=openapi.TYPE_OBJECT,
            description='instagram username of the page you want to transfer coins to',

        ),
        'amount': openapi.Schema(
            type=openapi.TYPE_INTEGER,
            description='amount of the coins you want to transfer'
        ),
    }
)

REPORT_ABUSE_DOC = openapi.Schema(
    required=['text', 'abuser'],
    type=openapi.TYPE_OBJECT,
    properties={
        'abuser': openapi.Schema(
            type=openapi.TYPE_OBJECT,
            description='ID of the order which is being reported',

        ),
        'text': openapi.Schema(
            type=openapi.TYPE_STRING,
            description='report text'
        ),
    }
)
Order_GateWay_DOC = openapi.Schema(
    required=['gateway', 'package_order'],
    type=openapi.TYPE_OBJECT,
    properties={
        'package_order': openapi.Schema(
            type=openapi.TYPE_OBJECT,
            description='ID of the package order',

        ),
        'gateway': openapi.Schema(
            type=openapi.TYPE_INTEGER,
            description='ID of the gateway'
        ),
    }
)
ORDER_POST_DOCS_RESPONSE = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={

        'gateway_url': openapi.Schema(
            type=openapi.TYPE_STRING,
            description='the url of the bank gateway'
        ),

    }
)

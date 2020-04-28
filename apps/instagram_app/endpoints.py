USER_MEDIAS = '17880160963012870'
USER_STORIES = '17890626976041463'
STORIES = '17873473675158481'

BASE_URL = 'https://www.instagram.com'
LOGIN_URL = 'https://www.instagram.com/accounts/login/ajax/'
ACCOUNT_PAGE = 'https://www.instagram.com/%s'
MEDIA_LINK = 'https://www.instagram.com/p/%s'
ACCOUNT_MEDIAS = 'https://www.instagram.com/graphql/query/?query_hash=42323d64886122307be10013ad2dcc44&variables=%s'
ACCOUNT_JSON_INFO = 'https://www.instagram.com/%s/?__a=1'
MEDIA_JSON_INFO = 'https://www.instagram.com/p/%s/?__a=1'
MEDIA_JSON_BY_LOCATION_ID = 'https://www.instagram.com/explore/locations/%s/?__a=1&max_id=%s'
MEDIA_JSON_BY_TAG = 'https://www.instagram.com/explore/tags/%s/?__a=1&max_id=%s'
GENERAL_SEARCH = 'https://www.instagram.com/web/search/topsearch/?query=%s'
COMMENTS_BY_SHORTCODE = 'https://www.instagram.com/graphql/query/?query_hash' \
                        '=97b41c52301f77ce508f55e66d17620e&variables=%s'
LIKES_BY_SHORTCODE_OLD = 'https://www.instagram.com/graphql/query/?query_id=17864450716183058&variables={' \
                         '"shortcode":"%s","first":%s,"after":"%s"} '
LIKES_BY_SHORTCODE = 'https://www.instagram.com/graphql/query/?query_hash=d5d763b1e2acf209d62d22d184488e57&variables=%s'

CHECK_LIKES_COUNT = 'https://www.instagram.com/graphql/query/?query_id=17864450716183058&variables={"shortcode": "%s","first":0}'
CHECK_COMMENTS_COUNT = 'https://www.instagram.com/graphql/query/?query_hash=97b41c52301f77ce508f55e66d17620e&variables={"shortcode": "%s","first":0}'

FOLLOWING_URL_OLD = 'https://www.instagram.com/graphql/query/?query_id=17874545323001329&id={{accountId}}&first={{' \
                    'count}}&after={{after}} '
FOLLOWING_URL = 'https://www.instagram.com/graphql/query/?query_hash=d04b0a864b4b54837c0d870b0e77e076&variables=%s'
FOLLOWERS_URL_OLD = 'https://www.instagram.com/graphql/query/?query_id=17851374694183129&id={{accountId}}&first={{' \
                    'count}}&after={{after}} '
FOLLOWERS_URL = 'https://www.instagram.com/graphql/query/?query_hash=c76146de99bb02f6415203be841dd25a&variables=%s'
FOLLOW_URL = 'https://www.instagram.com/web/friendships/%s/follow/'
UNFOLLOW_URL = 'https://www.instagram.com/web/friendships/%s/unfollow/'
INSTAGRAM_CDN_URL = 'https://scontent.cdninstagram.com/'
ACCOUNT_JSON_PRIVATE_INFO_BY_ID = 'https://i.instagram.com/api/v1/users/%s/info/'
LIKE_URL = 'https://www.instagram.com/web/likes/%s/like/'
UNLIKE_URL = 'https://www.instagram.com/web/likes/%s/unlike/'
ADD_COMMENT_URL = 'https://www.instagram.com/web/comments/%s/add/'
DELETE_COMMENT_URL = 'https://www.instagram.com/web/comments/%s/delete/%s/'

ACCOUNT_MEDIAS2 = 'https://www.instagram.com/graphql/query/?query_id=17880160963012870&id={{accountId}}&first=10&after='

GRAPH_QL_QUERY_URL = 'https://www.instagram.com/graphql/query/?query_id=%s'

POST_CAPTION_USERNAME = 'https://api.instagram.com/oembed/?url=http://instagr.am/p/B4cQ6WwDa6Z/'

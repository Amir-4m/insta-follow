START_USER_HAS_PAGE = "سلام {} عزیز خوش آمدی."
START_USER_HAS_NO_PAGE = """
سلام {} عزیز خوش آمدی.
متاسفانه تا کنون صفحه اینستاگرامی برای شما ثبت نشده است.
لطفا برای ثبت صفحه اینستاگرام خود آی دی صفحه خود را
به صورت username@ بنویسید و ارسال کنید.
"""

ADD_PAGE_LOADING = "در حال گرفتن اطلاعات ..."

BACK_TO_MENU = "بازگشت به منوی اصلی ↪ ..."

CHOICE_PROFILE = "مشاهده پروفایل 👤"
CHOICE_ADD_PAGE = "اضافه کردن صفحه اینستاگرام جدید ➕"
CHOICE_DELETE_PAGE = "حذف صفحه اینستاگرام ✖"
CHOICE_CREATE_ORDER = "ایجاد سفارش جدید 🧾"
CHOICE_GET_ORDERS = "لیست سفارشات من 📜"
CHOICE_COLLECT_COIN = "جمع آوری سکه 💰"
CHOICE_BY_LIKE = "جمع آوری سکه بوسیله لایک 👍"
CHOICE_BY_COMMENT = "جمع آوری سکه بوسیله کامنت ✏"
CHOICE_BY_FOLLOW = "جمع آوری سکه بوسیله دنبال کردن 👥"
CHOICE_ACTIVITY = "فعالیت ها 📑"

FILTER_OPEN = "فیلتر وضعیت های باز"
FILTER_VALIDATED = "فیلتر وضعیت های تایید شده"
FILTER_EXPIRED = "فیلتر وضعیت های منقضی شده"
FILTER_REJECTED = "فیلتر وضعیت های رد شده"
FILTER_DONE = "فیلتر وضعیت های انجام شده"
FILTER_LIKE = "فیلتر لایک"
FILTER_FOLLOW = "فیلتر فالو"
FILTER_COMMENT = "فیلتر کامنت"
FILTER_BY_PAGE = "فیلتر بر اساس صفحات"
NO_FILTER = "پاک کردن فیلتر ها"

PAGE_CREATED = """
نام کاربری 👤 💬: {{ page.instagram_username }}
تعداد پست: {{ page.post_no }}
فالو کنندگان ⬅️: {{ page.followers }}
فالو شده ها ➡️:{{ page.following }}

"""

GET_PROFILE = """
شناسه کاربری 🆔 : {{ user.username }}
نام 👤 : {{ user.first_name }}
تعداد سکه ها 💰 : {{ coin }}
صفحات اینستاگرامی شما:
{% for page in user_pages %}
{{ page.page.instagram_username }} -{{ forloop.counter }}
{% endfor %}
"""

WRONG_COMMAND = "دستور وارد شده اشتباه می باشد. ❌"

ENTER_PAGE_USERNAME = "لطفا آی دی صفحه اینستاگرام را بدون '@' تایپ و ارسال نمایید"

ERROR_MESSAGE = "خطایی رخ داده است! لطفا دوباره تلاش کنید. 🔄 ⭕"

PAGE_LIST = """
صفحات اینستاگرامی شما:
{% for page in user_pages %}
{{ page.page.instagram_username }} - /{{ page.id }}
{% endfor %}

"""

LIKE = 'لایک'

FOLLOW = 'فالو'

COMMENT = 'کامنت'

PAGE_DELETED = "صفحه {} از لیست صفحات شما حذف گردید. ✔"

PAGE_NOT_FOUND = "صفحه اینستاگرام وارد شده یافت نشد ! ❌"

COLLECT_COIN_TYPES = "با کدام روش مایل به جمع آوری سکه هستید ‌؟"

COLLECT_COIN_PAGE = "با کدام صفحه اینستاگرامی خود ادامه می دهید ؟"

INQUIRY_LIST = """
لطفا شماره سفارش های انجام شده را در زیر انتخاب کنید و سپس در انتها گزینه تایید را انتخاب کنید ⭕

پست های که باید لایک کنید 📋:
{% for inquiry in inquiries %}
شماره 🆔 : {{ inquiry.id }}
لینک 📎 :
<a href="{{ inquiry.order.link }}">{{ inquiry.order.link }}</a>

{% endfor %}
"""
INQUIRY_NOT_FOUND = """
متاسفانه هیچ رکوردی یافت نشد ! ❌
"""
BACK = "بازگشت ⬅"

DONE_INQUIRY = "انجام دادم ✅"

CHECK_INQUIRY = "🔸پس از بررسی و تایید لایک/کامنت/فالو شما, سکه ها به اکانت شما اضافه خواهد شد. 🔸"
INQUIRY_SUBMIT_ERROR = "⭕لطفا ابتدا شماره هایی که انجام داده اید را انتخاب کرده و سپس تایید را بزنید. ⭕"
NEXT_PAGE = "➡ صفحه بعدی"

PREVIOUS_PAGE = "صفحه قبلی ⬅"

ORDER_LIST = """
{% if orders %}
لیست سفارشات شما 📜:

{% for order in orders %}

نوع سفارش ℹ : {{ order.action.get_action_type_display }}
لینک 📎 : <a href="{{ order.link }}">{{ order.link }}</a>
هدف 🔹 : {{ order.target_no }}
بدست آمده 🔸 : {{ order.achieved_number_approved }}
وضعیت 🟠 :{% if order.is_enable %}فعال{% else %}غیر فعال{% endif %}

{% endfor %}
{% else %}
سفارشی یافت نشد !
{% endif %}
"""

ORDER_NOT_FOUND = "سفارشی یافت نشد !"

ORDER_CREATE_ACTION = "لطفانوع سفارش خود را انتخاب کنید"
ORDER_CREATE_LINK_LC = "لینک پست مورد نظر خود را وارد کنید"
ORDER_CREATE_LINK_F = "لینک پیج مورد نظر خود را وارد کنید"
ORDER_CREATE_TARGET = "تعداد هدف سفارش خود را وارد کنید"

NOT_ENOUGH_COIN = "متاسفانه تعداد سکه های شما برای ثبت این سفارش کافی نیست ! ❌💰"
ORDER_CANCEL = 'ثبت سفارش شما لغو شد ❌'
SUBMIT_ORDER = "ثبت سفارش ✅"

CANCEL = "انصراف ❌"

ORDER_CREATE_FINAL = "سفارش شما ثبت شد و پس از تایید نهایی قابل نمایش برای کاربران دیگر خواهد بوذ. ✅"

ORDER_CREATE_CHECK = """
نوع سفارش ℹ : {{ order_action }}
لینک 📎 : {{ link }}
هدف 🔹 : {{ target }}
ثبت کننده 👤 : {{ username }}
سکه قابل پرداخت برای ثبت سفارش 💰 : {{ price }}
"""

ORDER_CREATE_FAILED = """
ثبت سفارش شما با لینک 📎:
%s
با مشکل مواجه شد.❌ 
 ⭕ لطفا از خصوصی نبودن صفحه مورد تظر اطمینان حاصل فرمایید.
"""

ACTIVITY_LIST = """
{% if inquiries %}
لطفا برای انجام سفارش , شماره آن را انتخاب کنید ⭕
{% for inquiry in inquiries %}
شماره 🆔 : /{{ inquiry.id }}
نوع ℹ : {{ inquiry.order.action.get_action_type_display }}
لینک 📎 :
<a href="{{ inquiry.order.link }}">{{ inquiry.order.link }}</a>
وضعیت 🟠 :{{ inquiry.get_status_display }}
سکه دریافتی 💰 : {{ inquiry.order.action.action_value }}
قابل انجام برای صفحه {{ inquiry.user_page.page.instagram_username }} شما

{% endfor %} 
{% else %}
متاسفانه هیچ رکوردی یافت نشد !
{% endif %}
"""

SINGLE_INQUIRY_SELECT = """
شماره 🆔 : {{ inquiry.id }}
لینک 📎 :
<a href="{{ inquiry.order.link }}">{{ inquiry.order.link }}</a>
سکه دریافتی 💰 : {{ inquiry.order.action.action_value }}
"""

START_USER_HAS_PAGE = "سلام {} عزیز خوش آمدی."
START_USER_HAS_NO_PAGE = """
سلام {} عزیز خوش آمدی.
متاسفانه تا کنون صفحه اینستاگرامی برای شما ثبت نشده است.
لطفا برای ثبت صفحه اینستاگرام خود آی دی صفحه خود را
به صورت username@ بنویسید و ارسال کنید.
"""

CHOICE_PROFILE = "مشاهده پروفایل"
CHOICE_ADD_PAGE = "اضافه کردن صفحه اینستاگرام جدید"
CHOICE_DELETE_PAGE = "حذف صفحه اینستاگرام"
CHOICE_CREATE_ORDER = "ایجاد سفارش جدید"
CHOICE_GET_ORDERS = "لیست سفارشات من"
CHOICE_COLLECT_COIN = "جمع آوری سکه"
CHOICE_BY_LIKE = "جمع آوری سکه بوسیله لایک"
CHOICE_BY_COMMENT = "جمع آوری سکه کامنت"
CHOICE_BY_FOLLOW = "جمع آوری سکه دنبال کردن"

PAGE_CREATED = """

نام کاربری 💬: {{ page.username }}
تعداد پست 🎰: {{ page.post_no }}
فالو کنندگان ⬅️: {{ page.followers }}
فالو شده ها ➡️:{{ page.following }}

"""

GET_PROFILE = """
نام کاربری تلگرام : {{ user.username }}
تعداد سکه ها : {{ coin }}
صفحات اینستاگرامی شما:
{% for page in user_pages %}
{{ page }} -{{ forloop.counter }}
{% endfor %}
"""

WRONG_COMMAND = "❌ دستور وارد شده اشتباه می باشد. ❌"

ENTER_PAGE_USERNAME = "لطفا آی دی صفحه اینستاگرام را بدون '@' تایپ و ارسال نمایید"

ERROR_MESSAGE = "خطایی رخ داده است! لطفا دوباره تلاش کنید. ⭕"

PAGE_LIST = """
صفحات اینستاگرامی شما:
{% for page in user_pages %}
{{ page }} - /{{ page.id }}
{% endfor %}

"""

LIKE = 'لایک'

FOLLOW = 'فالو'

COMMENT = 'کامنت'

PAGE_DELETED = "صفحه {} از لیست صفحات شما حذف گردید."

PAGE_NOT_FOUND = "صفحه اینستاگرام وارد شده یافت نشد !"

COLLECT_COIN_TYPES = "با کدام روش مایل به جمع آوری سکه هستید ‌؟"

COLLECT_COIN_PAGE = "با کدام صفحه اینستاگرامی خود ادامه می دهید ؟"

INQUIRY_LIST = """
پست های که باید لایک کنید:
{% for inquiry in inquiries %}

{{ inquiry.order.link }} : لینک
___
{% endfor %}
"""
BACK = "بازگشت ⬅"

DONE_INQUIRY = "انجام دادم"

CHECK_INQUIRY = "پس از بررسی و تایید لایک/کامنت/فالو شما, سکه ها به اکانت شما اضافه خواهد شد."

NEXT_PAGE = "➡ صفحه بعدی"

PREVIOUS_PAGE = "صفحه قبلی ⬅"

ORDER_LIST = """
لیست سفارشات شما:

{% for order in orders %}

نوع سفارش : {{ order.action.action_type }}
لینک : {{ order.link }}
هدف : {{ order.target_no }}
بدست آمده : {{ ()order.achieved_number_approved }}
وضعیت : {{ order.is_enable }}
___
{% endfor %}
"""

ORDER_NOT_FOUND = "سفارشی یافت نشد !"

ORDER_CREATE_ACTION = "لطفانوع سفارش خود را انتخاب کنید"

ORDER_CREATE_LINK_LC = "لینک پست مورد نظر خود را وارد کنید"
ORDER_CREATE_LINK_F = "لینک پیج مورد نظر خود را وارد کنید"

ORDER_CREATE_TARGET = "تعداد هدف سفارش خود را وارد کنید"

NOT_ENOUGH_COIN = "متاسفانه تعداد سکه های شما برای ثبت این سفارش کافی نیست !"
ORDER_CANCEL = 'ثبت سفارش شما لغو شد'
SUBMIT_ORDER = "ثبت سفارش"

CANCEL = "انصراف"

ORDER_CREATE_FINAL = "سفارش شماثبت شد و پس از تایید نهایی قابل نمایش برای کاربران دیگر خواهد بوذ."

ORDER_CREATE_CHECK = """
نوع سفارش : {{ order_action }}
لینک : {{ link }}
هدف : {{ target }}
ثبت کننده : {{ username }}
سکه قابل پرداخت برای ثبت سفارش : {{ price }}
"""

# INQUIRYadaws_LIST = """
# پست های که باید لایک کنید:
# {% for inquiry in inquiries %}
#
# {{ inquiry.order.link }} : لینک
# {% if inquiry.status == 0 %}
# وضعیت : باز
#
# {% elif inquiry.status == 1 %}
# وضعیت : انجام شده
#
# {% elif inquiry.status == 2 %}
# وضعیت : تایید شده
#
# {% elif inquiry.status == 3 %}
# وضعیت : منقضی شده
#
# {% elif inquiry.status == 4 %}
# وضعیت : رد شده
#
# {% endif %}
#
# ___
# {% endfor %}
# """

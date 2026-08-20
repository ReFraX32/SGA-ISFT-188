from django.contrib.auth.decorators import login_required


def login_required_custom(view_func=None):
    decorator = login_required(login_url='login:login')
    if view_func is None:
        return decorator
    return decorator(view_func)

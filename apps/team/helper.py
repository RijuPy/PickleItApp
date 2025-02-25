from apps.chat.models import NotifiRoom, NotificationBox
from apps.user.helpers import send_push_notification
from apps.user.models import FCMTokenStore, User
from math import radians, cos, sin, asin, sqrt

"""
this is the dynamic function for send the notification a user.
"""
def notify_edited_player(user_id, titel, message):
    try:
        user = User.objects.filter(id=user_id).first()
        Check_room = NotifiRoom.objects.filter(user=user)
        if Check_room.exists():
            room = Check_room.first()
            NotificationBox.objects.create(room=room, notify_for=user, titel=titel, text_message=message)
        else:
            room_name = f"user_{user_id}"
            room = NotifiRoom.objects.create(user=user, name=room_name)
            NotificationBox.objects.create(room=room, notify_for = user, titel = "Profile Completion", text_message=f"Hi {user.first_name}! welcome to PickleIT! Remember to fully update your profile.")
            NotificationBox.objects.create(room=room, notify_for = user, titel = titel, text_message = message)
        check_token = FCMTokenStore.objects.filter(user__id=user_id)
        if check_token.exists():            
            get_token = check_token.first().fcm_token["fcm_token"]
            send_push_notification(get_token,titel,message)
        return True
    except Exception as e:
        return False


"""
this dynamic function use for search user base on loction.
"""
def haversine(lat1, lon1, lat2, lon2):
    """
    Calculate the great-circle distance between two points on the Earth (specified in decimal degrees).
    Returns distance in kilometers.
    """   
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    r = 6371  
    return c * r


def check_add_player(a, b):
    if a == b:
        return [],[]
    else:
        common_elements = set(a).intersection(b)
        uncommon_a = [x for x in a if x not in common_elements]
        uncommon_b = [x for x in b if x not in common_elements]

        if common_elements:
            return uncommon_a, uncommon_b
        else:
            return a, b
    return [],[]


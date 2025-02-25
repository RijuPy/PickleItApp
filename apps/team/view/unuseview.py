from django.shortcuts import render
import json, stripe, base64
from apps.user.models import *
from apps.chat.models import *
from apps.team.models import *
from apps.user.helpers import *
from apps.team.serializers import *
from apps.pickleitcollection.models import *
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache
from django.core.mail import send_mail
from django.contrib.auth.hashers import make_password 
from django.core.cache.backends.base import DEFAULT_TIMEOUT
from django.db.models import Q
from rest_framework.response import Response
from rest_framework import serializers, status
from rest_framework.decorators import api_view

protocol = settings.PROTOCALL
stripe.api_key = settings.STRIPE_PUBLIC_KEY
CACHE_TTL = getattr(settings, 'CACHE_TTL', DEFAULT_TIMEOUT)


#not use
@api_view(('get',))
def all_map_data(request):
    data = {'status':'','data':[], 'message':''}
    try:        
        user_uuid = request.GET.get('user_uuid')
        user_secret_key = request.GET.get('user_secret_key')
        user_current_location_lat = request.GET.get('user_current_location_lat')
        user_current_location_long = request.GET.get('user_current_location_long')
        check_user = User.objects.filter(uuid=user_uuid, secret_key=user_secret_key)
        if check_user.exists():
            result = []
            today_date = datetime.now()
            all_leagues = Leagues.objects.filter(registration_start_date__date__lte=today_date,registration_end_date__date__gte=today_date)
            leagues = all_leagues.values('id','uuid','secret_key','name','location','leagues_start_date','leagues_end_date',
                               'registration_start_date','registration_end_date','team_type__name','team_person__name',
                               "street","city","state","postal_code","country","complete_address","latitude","longitude","image","created_by__phone")
            output = []

            # Grouping data by 'name'
            grouped_data = {}
            for item in list(leagues):
                item["is_reg_diable"] = True
                match_ = Tournament.objects.filter(leagues_id=item["id"]).values()
                if match_.exists():
                    item["is_reg_diable"] = False
                le = Leagues.objects.filter(id=item["id"]).first()
                reg_team =le.registered_team.all().count()
                max_team = le.max_number_team
                if max_team <= reg_team:
                    item["is_reg_diable"] = False
                key = item['name']
                item["type_show"] = "tournament"
            facility_data = AdvertiserFacility.objects.all().values()
            for k in facility_data:
                k["type_show"]="facility"
            
            result = list(leagues) + list(facility_data)
            
            default_st = {"id": 0,"uuid": "","secret_key": "","name": "","location": "","leagues_start_date": "","leagues_end_date": "","registration_start_date": "","registration_end_date": "","team_type__name": "","team_person__name": "","street": "","city": "","state": "","postal_code": "","country": "","complete_address": "","latitude": 0,"longitude": 0,"image": "","created_by__phone": "","is_reg_diable": 0,"type_show": ""}
            if not user_current_location_lat:
                user_current_location_lat = "33.7488"
            if not user_current_location_long:
                user_current_location_long = "84.3877"
            
            default_st["location"] = ""
            default_st["latitude"] = user_current_location_lat
            default_st["longitude"] = user_current_location_long
            default_st["type_show"] = "Current Location"
            result.append(default_st)

            json_file_path = 'Pickleball_Venues.json'

            # Read the JSON file
            with open(json_file_path, 'r') as file:
                data2 = json.load(file)
            
            # for ij in data2:
            #     result.append(ij)
            # dat = json.dump(data)
            result = result + data2
            data["data"] = result
            data['message'] = "data found"
            data['status'] = status.HTTP_200_OK
        else:
            data['status'] = status.HTTP_404_NOT_FOUND
            data['message'] = "User not found."
        return Response(data)
    except Exception as e:
        data['status'] = status.HTTP_400_BAD_REQUEST
        data['message'] = f"{e}"
    return Response(data)

#not use
@api_view(('get',))
def all_map_data_new(request):
    # try:
    data = {'status':'','data':[], 'message':''}
    user_uuid = request.GET.get('user_uuid')
    user_secret_key = request.GET.get('user_secret_key')
    user_current_location_lat = request.GET.get('user_current_location_lat')
    user_current_location_long = request.GET.get('user_current_location_long')
    check_user = User.objects.filter(uuid=user_uuid, secret_key=user_secret_key)
    if check_user.exists():
        # result = []
        today_date = datetime.now()
        all_leagues = Leagues.objects.filter(registration_start_date__date__lte=today_date,registration_end_date__date__gte=today_date)
        leagues = all_leagues.values('id','uuid','secret_key','name','location','leagues_start_date','leagues_end_date',
                            'registration_start_date','registration_end_date','team_type__name','team_person__name',
                            "street","city","state","postal_code","country","complete_address","latitude","longitude","image","created_by__phone")
        output = []

        # Grouping data by 'name'
        grouped_data = {}
        for item in list(leagues):
            key = item['name']
            if key not in grouped_data:
                grouped_data[key] = {
                                    'latitude':item['latitude'],
                                    'type_show':'league', 
                                    'longitude':item["longitude"],
                                    'name': item['name'], 
                                    'org_phone':str(item['created_by__phone']),
                                    'location':item['location'],
                                    'registration_start_date':item["registration_start_date"],
                                    'registration_end_date':item["registration_end_date"],
                                    'leagues_start_date':item["leagues_start_date"],
                                    'leagues_end_date':item["leagues_end_date"],
                                    'location':item["location"],
                                    'image':item["image"],
                                    'type': [item['team_type__name']], 
                                    'data':[item]
                                    }
            else:
                grouped_data[key]['type'].append(item['team_type__name'])
                grouped_data[key]['data'].append(item)

        # Building the final output
        for key, value in grouped_data.items():
            output.append(value)

        facility_data = AdvertiserFacility.objects.all().values()
        for k in facility_data:
            k["type_show"]="facility"
            try:
                k["created_by__phone"] = str(User.objects.filter(id=k["created_by_id"]).first().phone)
            except:
                k["created_by__phone"] = None
        # print(output)
        result = list(output) + list(facility_data)
        #code after this point
        organized_data = {}

        # Iterate through the data
        for item in result:
            # Check if the 'lat', 'long', and 'type_show' are the same
            key = (item['latitude'], item['longitude'], item['type_show'])
            
            # If the key doesn't exist in the organized data, create it with an empty list
            if key not in organized_data:
                organized_data[key] = {'lat': key[0], 'long': key[1], 'type_show': key[2], 'data': []}
            
            # Append the item to the 'data' list corresponding to the key
            organized_data[key]['data'].append(item)

        # Convert the organized data dictionary values to a list
        result = list(organized_data.values())
        default_st = {"name": "","lat": 0,"long": 0,"type_show": "current_location", "data":[]}
        if not user_current_location_lat:
            user_current_location_lat = "34.0289259"
        if not user_current_location_long:
            user_current_location_long = "-84.198579"
        default_st["name"] = ""
        default_st["lat"] = float(user_current_location_lat)
        default_st["long"] = float(user_current_location_long)
        result.append(default_st)
        json_file_path = 'Pickleball_Venues.json'

        # Read the JSON file
        with open(json_file_path, 'r') as file:
            data2 = json.load(file)


        result = result+data2

        for c in result:
            if c["lat"] and c["long"]:
                c["lat"] = float(c["lat"])
                c["long"] = float(c["long"])
            else:
                c["lat"] = float("34.0289259")
                c["long"] = float("-84.198579")
        data["data"] = result
        data['message'] = "data found"
        data['status'] = status.HTTP_200_OK
    else:
        data['status'] = status.HTTP_404_NOT_FOUND
        data['message'] = "User not found."
    return Response(data)

#not use
@api_view(('GET',))
def list_player(request):
    data = {'status': '', 'data': [], 'message': ''}
    try:        
        user_uuid = request.GET.get('user_uuid')
        user_secret_key = request.GET.get('user_secret_key')
        search_text = request.GET.get('search_text')
        
        check_user = User.objects.filter(uuid=user_uuid, secret_key=user_secret_key)
        if check_user.exists():
            get_user = check_user.first()
            # if get_user.is_admin or get_user.is_organizer or :
            if not search_text:
                all_players = Player.objects.all().order_by('-id').values()
            else:
                all_players = Player.objects.filter(Q(player_first_name__icontains=search_text) | Q(player_last_name__icontains=search_text)).order_by('-id').values()
            
            following = AmbassadorsDetails.objects.filter(ambassador=get_user)

            if following.exists():
                # Retrieve the existing AmbassadorsDetails instance for the ambassador
                following_instance = following.first()
                following_ids = list(following_instance.following.all().values_list("id", flat=True))
            else:
                # If AmbassadorsDetails doesn't exist for the ambassador, create a new one
                following_instance = AmbassadorsDetails.objects.create(ambassador=get_user)
                # Save the following instance before retrieving the following_ids
                following_instance.save()
                following_ids = list(following_instance.following.all().values_list("id", flat=True))
            for player_data in all_players:
                player_id = player_data["id"]
                user_id = player_data["player_id"]
                user_image = User.objects.filter(id=user_id).values("rank","username","email","first_name","last_name","phone","uuid","secret_key","image","is_ambassador","is_sponsor","is_organizer","is_player","gender")
                user_instance = User.objects.filter(id=user_id).first()
                if user_id in following_ids:
                    player_data["is_follow"] = True
                else:
                    player_data["is_follow"] = False
                player_data["user"] = list(user_image)
                if user_image[0]["gender"] is not None:
                    player_data["gender"] = user_image[0]["gender"]
                else:
                    player_data["gender"] = "Male"
                
                player_rank = user_image[0]["rank"]
                if player_rank == "null" or player_rank == "" or  not player_rank:
                    player_rank = 1
                else:
                    player_rank = float(player_rank)

                player_data["player_ranking"] = player_rank
                player_data["user_uuid"] = user_image[0]["uuid"]
                player_data["player__is_ambassador"] = user_image[0]["is_ambassador"]
                player_data["user_secret_key"] = user_image[0]["secret_key"]
                
                p_image = user_image[0]["image"]
                if str(p_image) == "" or str(p_image) == "null":
                    player_data["player_image"] = None
                else:
                    player_data["player_image"] = user_image[0]["image"]
                
                player_data["is_edit"] = player_data["created_by_id"] == get_user.id
                player_instance = Player.objects.get(id=player_id)
                team_ids = list(player_instance.team.values_list('id', flat=True))
                player_data["team"] = []
                for team_id in team_ids:
                    team = Team.objects.filter(id=team_id).values()
                    if team.exists():
                        player_data["team"].append(list(team))

            data["status"] = status.HTTP_200_OK
            data["data"] = list(all_players)
            data["message"] = "Data found"

        else:
            data['status'] = status.HTTP_401_UNAUTHORIZED
            data['message'] = "Unauthorized access"

    except Exception as e:
        data['status'] = status.HTTP_400_BAD_REQUEST
        data['message'] = str(e)

    return Response(data)

#not use
@api_view(('GET',))
def api_list(request):
    data = {"USER":"","TEAM":""}
    # USER 
    data["USER"] = [
                    {"name": "SignUp", "path": "4eec011f0e4da0f19f576ac581ae8d77cd0191e51925c59ba843219390f205c9", "role": "ALL"},
                    {"name": "Login", "path": "7b87ea396289adfe5b192307cff9bd4a4e6512779efe14114f655363c17c3b20", "role": "ALL"},
                    {"name": "get_user_access_token", "path": "fd65514d783d0427c58482473b207b5eb5f92d864a738ccdd1f109c53ac9ca8a", "role": "ALL"},
                    {"name": "user_profile_view_api", "path": "89b449c603286a42377df664f16d7a2c9f5c5624250cadfacb1e0747c3e3f77d", "role": "ALL"},
                    {"name": "user_profile_edit_api", "path": "ed9b3852580d7da0fab6f3550acae26ee1ec94618a1fa74bddc62f9e892f3400", "role": "ALL"},
                    ]
    
    # TEAM
    data["TEAM"] = {"name":"leagues_teamType","path":"1963b18359229186f2817624c25bb11c613f9e30b9d2f6f18982064ae2e78d9e","role":"ALL",}
    data["TEAM"] = {"name":"leagues_teamType","path":"1963b18359229186f2817624c25bb11c613f9e30b9d2f6f18982064ae2e78d9e","role":"ALL",}
    return Response(data)


#not needed
@api_view(('POST',))
def email_send_for_create_user(request):
    data = {'status': '', 'message': ''}
    try:        
        email = request.data.get('email')
        user_uuid = request.data.get('user_uuid')
        user_secret_key = request.data.get('user_secret_key')
        sender = "Someone"
        check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
        if check_user.exists() :
            first_name = check_user.first().first_name
            last_name = check_user.first().last_name
            sender = f"{first_name} {last_name}"
        app_name = "PICKLEit"
        check_email = User.objects.filter(email=str(email).strip())
        if check_email.exists():
            #protocol = 'https' if request.is_secure() else 'http'
            host = request.get_host()
            current_site = f"{protocol}://{host}"
            # print(current_site)
            # verification_url = f"{current_site}/user/3342cb68e59a46aa0d8be6504ee298446bf1caff5aeae202ddec86de1e38436c/{get_user.uuid}/{get_user.secret_key}/{get_user.generated_otp}/"
            get_user = check_email.first()
            subject = f'{app_name} - Get Your User Credentials'
            message = ""
            html_message = f"""
                            <div style="background-color:#f4f4f4;">
                                <div style="margin:0px auto;border-radius:0px;max-width:600px;">
                                <table align="center" border="0" cellpadding="0" cellspacing="0" role="presentation" style="width:100%;border-radius:0px;">
                                    <tbody>
                                    <tr>
                                        <td style="font-size:0px;padding:5px 10px 5px 10px;text-align:center;">
                                        <div class="mj-column-per-100 mj-outlook-group-fix" style="font-size:0px;display:inline-block;vertical-align:top;width:100%;">
                                            <table border="0" cellpadding="0" cellspacing="0" role="presentation" style="vertical-align:top;" width="100%">
                                            <tbody>
                                                <tr>
                                                <td align="center" style="font-size:0px;padding:0 0px 20px 0px;word-break:break-word;">
                                                    <table border="0" cellpadding="0" cellspacing="0" role="presentation" style="border-collapse:collapse;border-spacing:0px;">
                                                    <tbody>
                                                        <tr>
                                                        <td style="width:560px;">
                                                            <table border="0" cellpadding="0" cellspacing="0" role="presentation" style="border-collapse:collapse;border-spacing:0px;width: 100%;">
                                                            <tbody>
                                                                <tr>
                                                                <td style="background-color: #fff;border-radius: 20px;padding: 15px 20px;">
                                                                    <table border="0" cellpadding="0" cellspacing="0" role="presentation" style="border-collapse:collapse;border-spacing:0px;width: 100%;">
                                                                    <tbody>
                                                                        <tr>
                                                                        <td height="20"></td>
                                                                        </tr>
                                                                        <tr>
                                                                        <td><img src="{current_site}/static/images/get_account.jpg" style="display: block;width: 100%;" width="100%;"></td>
                                                                        </tr>
                                                                        <tr>
                                                                        <td height="30"></td>
                                                                        </tr>
                                                                        <tr>
                                                                        <td>
                                                                            <table border="0" cellpadding="0" cellspacing="0" role="presentation"  bgcolor="#F6F6F6" style="border-collapse:collapse;border-spacing:0px;width: 100%; border-radius: 6px;">
                                                                            <tbody>
                                                                                <tr>
                                                                                <td height="20"></td>
                                                                                </tr>
                                                                                <tr>
                                                                                <td style="padding:20px 25px 0 25px;">
                                                                                    <p style=" font-size: 20px; font-weight: 500; line-height: 22px; color: #333333; margin: 0; padding: 0;">Dear {get_user.first_name},</p>
                                                                                </td>
                                                                                </tr>
                                                                                <tr>
                                                                                <td style="padding:0 25px 20px 25px;">
                                                                                    <p style="font-size: 17px;font-weight: 500;color:#333333">{sender} add you as a player of {app_name}</p>
                                                                                    <p style="font-size: 17px;font-weight: 500;color:#333333">Now You can access Your account</p>
                                                                                    <br>
                                                                                    <p style="font-size: 17px;font-weight: 500;color:#333333">Email: {email}</p>
                                                                                    <p style="font-size: 17px;font-weight: 500;color:#333333">New Password: {get_user.password_raw}</p>
                                                                                    <br>
                                                                                    <p style="font-size: 17px;font-weight: 500;color:#333333">Please use this new password to log in to your account. For security reasons, we highly recommend changing your password after logging in.</p>
                                                                                    <p style="font-size: 17px;font-weight: 500;color:#333333">If you face any Problem, please contact our support team immediately at pickleitnow1@gmail.com to secure your account.</p>
                                                                                </td>
                                                                                </tr>
                                                                                <tr>
                                                                                <td style="padding:20px 25px;">
                                                                                    <p style="font-size: 17px;font-weight: 500;color:#333333">Thank you, </p>
                                                                                    <p style="font-size: 17px;font-weight: 500;color:#333333">{app_name} Team</p>
                                                                                </td>
                                                                                </tr>
                                                                            </tbody>
                                                                            </table>
                                                                        </td>
                                                                        </tr>
                                                                        <tr>
                                                                        <td height="20"></td>
                                                                        </tr>
                                                                        
                                                                        <tr>
                                                                        <td height="10"></td>
                                                                    </tbody>
                                                                    </table>
                                                                </td>
                                                                </tr>
                                                            </tbody>
                                                            </table>
                                                        </td>
                                                        </tr>
                                                    </tbody>
                                                    </table>
                                                </td>
                                                </tr>
                                            </tbody>
                                            </table>
                                        </div>
                                        </td>
                                    </tr>
                                    </tbody>
                                </table>
                                </div>
                                <div style="margin:0px auto;border-radius:0px;max-width:600px;">
                                <table align="center" border="0" cellpadding="0" cellspacing="0" role="presentation" style="width:100%;border-radius:0px;">
                                    <tbody>
                                    <tr>
                                        <td style="font-size:0px;padding:5px 10px 5px 10px;text-align:center;">
                                        <div class="mj-column-per-75 mj-outlook-group-fix" style="font-size:0px;display:inline-block;vertical-align:top;width:100%;">
                                            <table border="0" cellpadding="0" cellspacing="0" role="presentation" style="vertical-align:top;" width="100%">
                                            <tbody>
                                                <tr>
                                                <td style="text-align: center;"><img src="{current_site}/static/images/PickleIt_logo.png" width="100"></td>
                                                </tr>
                                                <tr>
                                                <td style="text-align: center;"><p style=" font-size: 15px; font-weight: 500; color: #c1c1c1; line-height: 20px; margin: 0;">© 2024 {app_name}. All Rights Reserved.</p></td>
                                                </tr>
                                            </tbody>
                                            </table>
                                        </div>
                                        </td>
                                    </tr>
                                    </tbody>
                                </table>
                                </div>
                                <div style="margin:0px auto;border-radius:0px;max-width:600px;">
                                <table align="center" border="0" cellpadding="0" cellspacing="0" role="presentation" style="width:100%;border-radius:0px;">
                                    <tbody>
                                    <tr>
                                        <td style="font-size:0px;padding:0px 0px 0px 0px;text-align:center;">
                                        <div class="mj-column-per-100 mj-outlook-group-fix" style="font-size:0px;display:inline-block;vertical-align:top;width:100%;">
                                            <table border="0" cellpadding="0" cellspacing="0" role="presentation" style="vertical-align:top;" width="100%">
                                            <tbody>
                                                <tr>
                                                <td style="font-size:0px;word-break:break-word;">
                                                    <div style="height:20px;line-height:20px;">
                                                    &#8202;
                                                    </div>
                                                </td>
                                                </tr>
                                            </tbody>
                                            </table>
                                        </div>
                                        </td>
                                    </tr>
                                    </tbody>
                                </table>
                                </div>
                            </div>
                            """

            send_mail(
                subject,
                message,
                'pickleitnow1@gmail.com',  # Replace with your email address
                [get_user.email],
                fail_silently=False,
                html_message=html_message,
            )
            data['status'], data['message'] = status.HTTP_200_OK, f"User cradencial is send to {get_user.email}"
        else:
            data['status'], data['message'] = status.HTTP_403_FORBIDDEN, f"Email not found"
    except Exception as e:
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, str(e)
    return Response(data)


#not use
@api_view(('GET',))
def team_list(request):
    data = {'status': '', 'message': ''}
    try:        
        user_uuid = request.GET.get('user_uuid')
        user_secret_key = request.GET.get('user_secret_key')
        search_text = request.GET.get('search_text')

        check_user = User.objects.filter(uuid=user_uuid, secret_key=user_secret_key)
        if check_user.exists():
            main_data = []
            user = check_user.first()
            if user.is_admin or user.is_organizer:
                # Admin or organizer can see all teams
                teams_query = Team.objects.all()
            else:
                # Other users can only see their own teams
                teams_query = Team.objects.filter(created_by=user)

            if search_text is not None:
                teams_query = teams_query.filter(Q(name__icontains=search_text))

            teams = teams_query.order_by('-id').values('id', 'uuid', 'secret_key', 'name', 'location', 'created_by__first_name', 'created_by__last_name',
                                                        'team_image', 'created_by__uuid', 'created_by__secret_key', 'team_type', 'team_person', 'created_by_id')
            store_ids = []
            for team in teams:
                store_ids.append(team["id"])
                if team['created_by_id'] == user.id:
                    is_edit = True  
                else:
                    is_edit = False
                get_player = Player.objects.filter(team__id=team['id']).values('uuid', 'secret_key', 'player_full_name', 'player_ranking', 'player__rank')
                for player in get_player:
                    if player['player__rank'] == "" or player['player__rank'] == "null" or not player['player__rank']:
                        player['player_ranking'] = 1
                    else:
                        player['player_ranking'] = float(player['player__rank'])
                
                #team image
                if team['team_image'] == "" or team['team_image'] == "null":
                    team_image = None
                else:
                    team_image = team['team_image']  
                 
                main_data.append({
                    'id':team["id"],
                    'team_uuid': team['uuid'],
                    'team_secret_key': team['secret_key'],
                    'team_name': team['name'],
                    'location': team['location'],
                    'created_by': f"{team['created_by__first_name']} {team['created_by__last_name']}",
                    'created_by_uuid': team['created_by__uuid'],
                    'created_by_secret_key': team['created_by__secret_key'],
                    'team_image': team_image,
                    'player_data': get_player,
                    'team_type': team['team_type'],
                    'team_person': team['team_person'],
                    'is_edit': is_edit
                })
            if user.is_player and (not user.is_admin or not user.is_organizer):
                check_player = Player.objects.filter(player=user)
                if check_player.exists():
                    player = check_player.first()
                    all_team_ids = player.team.all().values_list("id", flat=True)
                    # data["ids"] = all_team_ids
                    for mj in all_team_ids:
                        if mj not in store_ids:
                            team_instance = Team.objects.filter(id=mj).values('id', 'uuid', 'secret_key', 'name', 'location', 'created_by__first_name', 'created_by__last_name',
                                                        'team_image', 'created_by__uuid', 'created_by__secret_key', 'team_type', 'team_person', 'created_by_id').first()
                            is_edit = False
                            get_player = Player.objects.filter(team__id=mj).values('uuid', 'secret_key', 'player_full_name', 'player_ranking', 'player__rank')
                            for player in get_player:
                                player['player_ranking'] = player['player__rank']
                            
                            #team image
                            if team_instance['team_image'] == "" or team_instance['team_image'] == "null":
                                team_image = None
                            else:
                                team_image = team_instance['team_image']
                            
                            main_data.append({
                                'id': team_instance['id'],
                                'team_uuid': team_instance['uuid'],
                                'team_secret_key': team_instance['secret_key'],
                                'team_name': team_instance['name'],
                                'location': team_instance['location'],
                                'created_by': f"{team_instance['created_by__first_name']} {team_instance['created_by__last_name']}",
                                'created_by_uuid': team_instance['created_by__uuid'],
                                'created_by_secret_key': team_instance['created_by__secret_key'],
                                'team_image': team_image,
                                'player_data': get_player,
                                'team_type': team_instance['team_type'],
                                'team_person': team_instance['team_person'],
                                'is_edit': is_edit
                            })
            
            data["status"], data["data"], data["message"] = status.HTTP_200_OK, main_data, "Data found for Admin" if user.is_admin or user.is_organizer else "Data found"
        else:
            data["status"], data["message"] = status.HTTP_404_NOT_FOUND, "User not found"  
    except Exception as e:
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, str(e)
    return Response(data)


#not use
@api_view(('POST',))
def send_team_member_notification(request):
    data = {'status':'','message':''}
    try:
        user_uuid = request.data.get('user_uuid')
        user_secret_key = request.data.get('user_secret_key')
        team_person = request.data.get('team_person')
        player1_email = request.data.get('player1_email')
        player1_first_name = request.data.get('player1_first_name')
        player1_last_name = request.data.get('player1_last_name')
        player1_phone = request.data.get('player1_phone')

        player2_email = request.data.get('player2_email')
        player2_first_name = request.data.get('player2_first_name')
        player2_last_name = request.data.get('player2_last_name')
        player2_phone = request.data.get('player2_phone')

        player3_email = request.data.get('player3_email')
        player3_first_name = request.data.get('player3_first_name')
        player3_last_name = request.data.get('player3_last_name')
        player3_phone = request.data.get('player3_phone')

        player4_email = request.data.get('player4_email')
        player4_first_name = request.data.get('player4_first_name')
        player4_last_name = request.data.get('player4_last_name')
        player4_phone = request.data.get('player4_phone')
        app_name = "PICKLEit"
        check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
        subject = f'You are invited to register in {app_name}'
        #protocol = 'https' if request.is_secure() else 'http'
        host = request.get_host()
        current_site = f"{protocol}://{host}"
        message = ""
        android_url = "https://docs.google.com/uc?export=download&id=1OzRKC3QT-tZg8oSSE9U302stRRXn0aRG"
        ios_url = ""
        if check_user.exists() and team_person and  team_person != "":
            created_by = f"{str(check_user.first().first_name)} {str(check_user.first().last_name)}"
            if team_person == "Two Person Team" :
                for i in range(1,3):
                    player_email = request.data.get('player{}_email'.format(i))
                    player_first_name = request.data.get('player{}_first_name'.format(i))
                    player_last_name = request.data.get('player{}_last_name'.format(i))
                    html_message = f"""
                                <div style="background-color:#f4f4f4;">
                                    <div style="margin:0px auto;border-radius:0px;max-width:600px;">
                                    <table align="center" border="0" cellpadding="0" cellspacing="0" role="presentation" style="width:100%;border-radius:0px;">
                                        <tbody>
                                        <tr>
                                            <td style="font-size:0px;padding:5px 10px 5px 10px;text-align:center;">
                                            <div class="mj-column-per-100 mj-outlook-group-fix" style="font-size:0px;display:inline-block;vertical-align:top;width:100%;">
                                                <table border="0" cellpadding="0" cellspacing="0" role="presentation" style="vertical-align:top;" width="100%">
                                                <tbody>
                                                    <tr>
                                                    <td align="center" style="font-size:0px;padding:0 0px 20px 0px;word-break:break-word;">
                                                        <table border="0" cellpadding="0" cellspacing="0" role="presentation" style="border-collapse:collapse;border-spacing:0px;">
                                                        <tbody>
                                                            <tr>
                                                            <td style="width:560px;">
                                                                <table border="0" cellpadding="0" cellspacing="0" role="presentation" style="border-collapse:collapse;border-spacing:0px;width: 100%;">
                                                                <tbody>
                                                                    <tr>
                                                                    <td style="background-color: #fff;border-radius: 20px;padding: 15px 20px;">
                                                                        <table border="0" cellpadding="0" cellspacing="0" role="presentation" style="border-collapse:collapse;border-spacing:0px;width: 100%;">
                                                                        <tbody>
                                                                            <tr>
                                                                            <td height="20"></td>
                                                                            </tr>
                                                                            <tr>
                                                                            <td><img src="{current_site}/static/images/send_team_member_notification.png" style="display: block;width: 100%;" width="100%;"></td>
                                                                            </tr>
                                                                            <tr>
                                                                            <td height="30"></td>
                                                                            </tr>
                                                                            <tr>
                                                                            <td>
                                                                                <table border="0" cellpadding="0" cellspacing="0" role="presentation"  bgcolor="#F6F6F6" style="border-collapse:collapse;border-spacing:0px;width: 100%; border-radius: 6px;">
                                                                                <tbody>
                                                                                    <tr>
                                                                                    <td height="20"></td>
                                                                                    </tr>
                                                                                    <tr>
                                                                                    <td style="padding:20px 25px 0 25px;">
                                                                                        <p style=" font-size: 20px; font-weight: 500; line-height: 22px; color: #333333; margin: 0; padding: 0;">Dear {player_first_name},</p>
                                                                                    </td>
                                                                                    </tr>
                                                                                    <tr>
                                                                                    <td style="padding:0 25px 20px 25px;">
                                                                                        <p style="font-size: 17px;font-weight: 500;color:#333333">{created_by} have invited you to register in this app.\nClick here and download the app to complete your registration.</p>
                                                                                        <a href="{android_url}" style="margin-right:10px; margin-bottom:10px; font-size: 17px;font-weight: 500;color:#333333; background-color:#008CBA;color:white;padding:10px;text-align:center;text-decoration:none;display:inline-block;border-radius:5px;">android download</a>
                                                                                        <a href="{ios_url}" style="font-size: 17px;font-weight: 500;color:#333333; background-color:#008CBA;color:white;padding:10px;text-align:center;text-decoration:none;display:inline-block;border-radius:5px;">ios download</a>
                                                                                    </td>
                                                                                    </tr>
                                                                                    <tr>
                                                                                    <td style="padding:20px 25px;">
                                                                                        <p style="font-size: 17px;font-weight: 500;color:#333333">Thank you, </p>
                                                                                        <p style="font-size: 17px;font-weight: 500;color:#333333">Pickleball Team</p>
                                                                                    </td>
                                                                                    </tr>
                                                                                </tbody>
                                                                                </table>
                                                                            </td>
                                                                            </tr>
                                                                            
                                                                        </tbody>
                                                                        </table>
                                                                    </td>
                                                                    </tr>
                                                                </tbody>
                                                                </table>
                                                            </td>
                                                            </tr>
                                                        </tbody>
                                                        </table>
                                                    </td>
                                                    </tr>
                                                </tbody>
                                                </table>
                                            </div>
                                            </td>
                                        </tr>
                                        </tbody>
                                    </table>
                                    </div>
                                    <div style="margin:0px auto;border-radius:0px;max-width:600px;">
                                    <table align="center" border="0" cellpadding="0" cellspacing="0" role="presentation" style="width:100%;border-radius:0px;">
                                        <tbody>
                                        <tr>
                                            <td style="font-size:0px;padding:5px 10px 5px 10px;text-align:center;">
                                            <div class="mj-column-per-75 mj-outlook-group-fix" style="font-size:0px;display:inline-block;vertical-align:top;width:100%;">
                                                <table border="0" cellpadding="0" cellspacing="0" role="presentation" style="vertical-align:top;" width="100%">
                                                <tbody>
                                                    <tr>
                                                    <td style="text-align: center;"><img src="{current_site}/static/images/logo.png" width="100"></td>
                                                    </tr>
                                                    <tr>
                                                    <td style="text-align: center;"><p style=" font-size: 15px; font-weight: 500; color: #c1c1c1; line-height: 20px; margin: 0;">© 2023 Pickleball. All Rights Reserved.</p></td>
                                                    </tr>
                                                </tbody>
                                                </table>
                                            </div>
                                            </td>
                                        </tr>
                                        </tbody>
                                    </table>
                                    </div>
                                    <div style="margin:0px auto;border-radius:0px;max-width:600px;">
                                    <table align="center" border="0" cellpadding="0" cellspacing="0" role="presentation" style="width:100%;border-radius:0px;">
                                        <tbody>
                                        <tr>
                                            <td style="font-size:0px;padding:0px 0px 0px 0px;text-align:center;">
                                            <div class="mj-column-per-100 mj-outlook-group-fix" style="font-size:0px;display:inline-block;vertical-align:top;width:100%;">
                                                <table border="0" cellpadding="0" cellspacing="0" role="presentation" style="vertical-align:top;" width="100%">
                                                <tbody>
                                                    <tr>
                                                    <td style="font-size:0px;word-break:break-word;">
                                                        <div style="height:20px;line-height:20px;">
                                                        &#8202;
                                                        </div>
                                                    </td>
                                                    </tr>
                                                </tbody>
                                                </table>
                                            </div>
                                            </td>
                                        </tr>
                                        </tbody>
                                    </table>
                                    </div>
                                </div>
                                """
                    send_mail(
                            subject,
                            message,
                            'pickleitnow1@gmail.com',
                            [player_email],
                            fail_silently=False,
                            html_message=html_message,
                        )
                
                data['status'], data['message'] = status.HTTP_200_OK, f"Email verification link sent"
            
            elif team_person == "Four Person Team" :
                for i in range(1,5):
                    player_email = request.data.get('player{}_email'.format(i))
                    player_first_name = request.data.get('player{}_first_name'.format(i))
                    player_last_name = request.data.get('player{}_last_name'.format(i))
                    html_message = f"""
                                <div style="background-color:#f4f4f4;">
                                    <div style="margin:0px auto;border-radius:0px;max-width:600px;">
                                    <table align="center" border="0" cellpadding="0" cellspacing="0" role="presentation" style="width:100%;border-radius:0px;">
                                        <tbody>
                                        <tr>
                                            <td style="font-size:0px;padding:5px 10px 5px 10px;text-align:center;">
                                            <div class="mj-column-per-100 mj-outlook-group-fix" style="font-size:0px;display:inline-block;vertical-align:top;width:100%;">
                                                <table border="0" cellpadding="0" cellspacing="0" role="presentation" style="vertical-align:top;" width="100%">
                                                <tbody>
                                                    <tr>
                                                    <td align="center" style="font-size:0px;padding:0 0px 20px 0px;word-break:break-word;">
                                                        <table border="0" cellpadding="0" cellspacing="0" role="presentation" style="border-collapse:collapse;border-spacing:0px;">
                                                        <tbody>
                                                            <tr>
                                                            <td style="width:560px;">
                                                                <table border="0" cellpadding="0" cellspacing="0" role="presentation" style="border-collapse:collapse;border-spacing:0px;width: 100%;">
                                                                <tbody>
                                                                    <tr>
                                                                    <td style="background-color: #fff;border-radius: 20px;padding: 15px 20px;">
                                                                        <table border="0" cellpadding="0" cellspacing="0" role="presentation" style="border-collapse:collapse;border-spacing:0px;width: 100%;">
                                                                        <tbody>
                                                                            <tr>
                                                                            <td height="20"></td>
                                                                            </tr>
                                                                            <tr>
                                                                            <td><img src="{current_site}/static/images/send_team_member_notification.png" style="display: block;width: 100%;" width="100%;"></td>
                                                                            </tr>
                                                                            <tr>
                                                                            <td height="30"></td>
                                                                            </tr>
                                                                            <tr>
                                                                            <td>
                                                                                <table border="0" cellpadding="0" cellspacing="0" role="presentation"  bgcolor="#F6F6F6" style="border-collapse:collapse;border-spacing:0px;width: 100%; border-radius: 6px;">
                                                                                <tbody>
                                                                                    <tr>
                                                                                    <td height="20"></td>
                                                                                    </tr>
                                                                                    <tr>
                                                                                    <td style="padding:20px 25px 0 25px;">
                                                                                        <p style=" font-size: 20px; font-weight: 500; line-height: 22px; color: #333333; margin: 0; padding: 0;">Dear {player_first_name} {player_last_name},</p>
                                                                                    </td>
                                                                                    </tr>
                                                                                    <tr>
                                                                                    <td style="padding:0 25px 20px 25px;">
                                                                                        <p style="font-size: 17px;font-weight: 500;color:#333333">{created_by} have invited you to register in this app.\nClick here and download the app to complete your registration.</p>
                                                                                        <a href="{android_url}" style="margin-right:10px; font-size: 17px;font-weight: 500;color:#333333; background-color:#008CBA;color:white;padding:10px;text-align:center;text-decoration:none;display:inline-block;border-radius:5px;">android download</a>
                                                                                        <a href="{ios_url}" style="font-size: 17px;font-weight: 500;color:#333333; background-color:#008CBA;color:white;padding:10px;text-align:center;text-decoration:none;display:inline-block;border-radius:5px;">ios download</a>
                                                                                    </td>
                                                                                    </tr>
                                                                                    <tr>
                                                                                    <td style="padding:20px 25px;">
                                                                                        <p style="font-size: 17px;font-weight: 500;color:#333333">Thank you, </p>
                                                                                        <p style="font-size: 17px;font-weight: 500;color:#333333">Pickleball Team</p>
                                                                                    </td>
                                                                                    </tr>
                                                                                </tbody>
                                                                                </table>
                                                                            </td>
                                                                            </tr>
                                                                            
                                                                        </tbody>
                                                                        </table>
                                                                    </td>
                                                                    </tr>
                                                                </tbody>
                                                                </table>
                                                            </td>
                                                            </tr>
                                                        </tbody>
                                                        </table>
                                                    </td>
                                                    </tr>
                                                </tbody>
                                                </table>
                                            </div>
                                            </td>
                                        </tr>
                                        </tbody>
                                    </table>
                                    </div>
                                    <div style="margin:0px auto;border-radius:0px;max-width:600px;">
                                    <table align="center" border="0" cellpadding="0" cellspacing="0" role="presentation" style="width:100%;border-radius:0px;">
                                        <tbody>
                                        <tr>
                                            <td style="font-size:0px;padding:5px 10px 5px 10px;text-align:center;">
                                            <div class="mj-column-per-75 mj-outlook-group-fix" style="font-size:0px;display:inline-block;vertical-align:top;width:100%;">
                                                <table border="0" cellpadding="0" cellspacing="0" role="presentation" style="vertical-align:top;" width="100%">
                                                <tbody>
                                                    <tr>
                                                    <td style="text-align: center;"><img src="{current_site}/static/images/logo.png" width="100"></td>
                                                    </tr>
                                                    <tr>
                                                    <td style="text-align: center;"><p style=" font-size: 15px; font-weight: 500; color: #c1c1c1; line-height: 20px; margin: 0;">© 2023 Pickleball. All Rights Reserved.</p></td>
                                                    </tr>
                                                </tbody>
                                                </table>
                                            </div>
                                            </td>
                                        </tr>
                                        </tbody>
                                    </table>
                                    </div>
                                    <div style="margin:0px auto;border-radius:0px;max-width:600px;">
                                    <table align="center" border="0" cellpadding="0" cellspacing="0" role="presentation" style="width:100%;border-radius:0px;">
                                        <tbody>
                                        <tr>
                                            <td style="font-size:0px;padding:0px 0px 0px 0px;text-align:center;">
                                            <div class="mj-column-per-100 mj-outlook-group-fix" style="font-size:0px;display:inline-block;vertical-align:top;width:100%;">
                                                <table border="0" cellpadding="0" cellspacing="0" role="presentation" style="vertical-align:top;" width="100%">
                                                <tbody>
                                                    <tr>
                                                    <td style="font-size:0px;word-break:break-word;">
                                                        <div style="height:20px;line-height:20px;">
                                                        &#8202;
                                                        </div>
                                                    </td>
                                                    </tr>
                                                </tbody>
                                                </table>
                                            </div>
                                            </td>
                                        </tr>
                                        </tbody>
                                    </table>
                                    </div>
                                </div>
                                """
                    send_mail(
                            subject,
                            message,
                            'pickleitnow1@gmail.com',
                            [player_email],
                            fail_silently=False,
                            html_message=html_message,
                        )
                
                data['status'], data['message'] = status.HTTP_200_OK, f"Email verification link sent"
            else:
                data["status"], data["message"] = status.HTTP_404_NOT_FOUND, "HTTP_404_NOT_FOUND. team_person parameter not found."
        else:
            data["status"], data["message"] = status.HTTP_404_NOT_FOUND, "User not found."
    except Exception as e :
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
    return Response(data)

class AddSponsorSerializer(serializers.Serializer):
    user_uuid = serializers.UUIDField()
    user_secret_key = serializers.CharField()
    username = serializers.CharField()
    email = serializers.EmailField()
    contact = serializers.CharField()
    league_uuid = serializers.UUIDField()
    league_secret_key = serializers.CharField()
    role = serializers.CharField()
    description = serializers.CharField()

@api_view(('POST',))
def add_sponsor(request):
    data = {'status': '', 'message': '','send_maile_status': False}
    try:
        serializer = AddSponsorSerializer(data=request.data)
        if not serializer.is_valid():
            data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, serializer.errors
            return Response(data)

        user_uuid = serializer.validated_data['user_uuid']
        user_secret_key = serializer.validated_data['user_secret_key']
        username = serializer.validated_data['username']
        email = serializer.validated_data['email']
        contact = serializer.validated_data['contact']
        league_uuid = serializer.validated_data['league_uuid']
        league_secret_key = serializer.validated_data['league_secret_key']
        role = serializer.validated_data['role']
        description = serializer.validated_data['description']
        check_user = User.objects.filter(secret_key=user_secret_key, uuid=user_uuid)
        obj = GenerateKey()
        secret_key = obj.gen_advertisement_key()

        if not check_user.exists():
            data['status'], data['message'] = status.HTTP_404_NOT_FOUND, "User not found"
            return Response(data)

        check_league = Leagues.objects.filter(uuid=league_uuid, secret_key=league_secret_key)
        if not check_league.exists():
            data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, "League does not exist"
            return Response(data)

        role_check = Role.objects.filter(role=role)
        if not role_check.exists():
            data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, "Role does not exist"
            return Response(data)

        password = GenerateKey.generate_password(5)
        mp = make_password(password)

        sponsor = User.objects.create(
            first_name=username,
            username=email,
            email=email,
            phone=contact,
            password=mp,
            password_raw=password,
            secret_key=secret_key,
            is_sponsor_expires_at=check_league.first().leagues_end_date,
            role=role_check.first(),
            is_verified=True,
            is_sponsor = True
        )

        IsSponsorDetails.objects.create(
            secret_key=secret_key,
            sponsor=sponsor,
            sponsor_added_by=check_user.first(),
            league_uuid=league_uuid,
            league_secret_key=league_secret_key,
            description=description
        )
        league = check_league.first().name
        current_site = 'https' + '://' + request.META['HTTP_HOST']
        send_type = "send"
        send_email_status = send_email_for_invite_sponsor(current_site, email, league, send_type)
        # print(send_email_status)
        data['status'], data['message'],data['send_maile_status'] = status.HTTP_201_CREATED, "Sponsor created successfully", send_email_status
    except Exception as e:
        data['status'], data['message'] = "400", str(e)
    return Response(data)

class IsSponsorDetailsSerializer(serializers.ModelSerializer):
    sponsor_name = serializers.CharField(source='sponsor.first_name', read_only=True)
    sponsor_email = serializers.CharField(source='sponsor.email', read_only=True)
    sponsor_uuid = serializers.CharField(source='uuid', read_only=True)
    sponsor_image = serializers.CharField(source='sponsor.image', read_only=True)
    sponsor_secret_key = serializers.CharField(source='secret_key', read_only=True)
    user_uuid = serializers.CharField(source='sponsor.uuid', read_only=True)
    user_secret_key = serializers.CharField(source='sponsor.secret_key', read_only=True)
    is_sponsor = serializers.CharField(source='sponsor.is_sponsor', read_only=True)
    is_sponsor_expires_at = serializers.CharField(source='sponsor.is_sponsor_expires_at', read_only=True)
    is_verified = serializers.CharField(source='sponsor.is_verified', read_only=True)
    # league = Leagues.objects.filter()
    
    class Meta:
        model = IsSponsorDetails
        fields = ["sponsor_uuid", "sponsor_secret_key", "user_uuid", "user_secret_key", "league_uuid","league_secret_key", "sponsor_name", "sponsor_image", "sponsor_email", "sponsor_email", "is_sponsor", "is_sponsor_expires_at", "is_verified", "sponsor_added_by", "description"]

@api_view(['GET'])
def view_sponsor_list(request):
    data = {'status': '', 'message': '', 'data': []}
    try:
        user_uuid = request.GET.get('user_uuid')
        user_secret_key = request.GET.get('user_secret_key')
        search_text = request.GET.get('search_text')
        
        check_user = User.objects.filter(secret_key=user_secret_key, uuid=user_uuid)
        if check_user.exists():
            get_user = check_user.first()
            
            try:
                if get_user.is_admin:
                    if search_text:
                        sponsor_details = IsSponsorDetails.objects.filter(Q(sponsor__first_name__icontains=search_text) | Q(sponsor__last_name__icontains=search_text))
                    else:
                        sponsor_details = IsSponsorDetails.objects.all()
                else:
                    if search_text:
                        sponsor_details = IsSponsorDetails.objects.filter(sponsor_added_by=get_user).filter(Q(sponsor__first_name__icontains=search_text) | Q(sponsor__last_name__icontains=search_text))
                    else:
                        sponsor_details = IsSponsorDetails.objects.filter(sponsor_added_by=get_user)

                if sponsor_details.exists():
                    serializer = IsSponsorDetailsSerializer(sponsor_details, many=True)
                    data['data'] = serializer.data
                    data['status'], data['message'] = status.HTTP_200_OK, ""
                else:
                    data['status'], data['message'] = status.HTTP_200_OK, "no result found"
            except Exception as e:
                data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, str(e)
        else:
            data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, "User not found"
    except Exception as e:
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, str(e)
    
    return Response(data)


@api_view(('GET',))
def view_sponsor(request):
    data = {'status': '', 'message': '', 'data': {},'league_name':''}
    try:
        sponsor_uuid = request.GET.get('sponsor_uuid')
        sponsor_secret_key = request.GET.get('sponsor_secret_key')
        check_user = IsSponsorDetails.objects.filter(uuid=sponsor_uuid, secret_key=sponsor_secret_key)
        if check_user.exists():
            sponsor_instance = check_user.first()
            serializer = IsSponsorDetailsSerializer(sponsor_instance)
            get_user = sponsor_instance.sponsor
            ads_list = Advertisement.objects.filter(created_by=get_user).values()
            data["league_name"] = Leagues.objects.filter(uuid=serializer.data["league_uuid"]).first().name
            data['data'] = [serializer.data]
            data['ads_data'] = list(ads_list)
            data['status'] = status.HTTP_200_OK
        else:
            data['status'], data['message'] = status.HTTP_404_NOT_FOUND, "Sponsor not found"
    except Exception as e:
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, str(e)
    
    return Response(data)


@api_view(('POST',))
def resend_email_sponsor(request):
    data = {'status': '', 'message': '', 'data': []}
    try:
        sponsor_uuid = request.data.get('sponsor_uuid')
        sponsor_secret_key = request.data.get('sponsor_secret_key')
        email = request.data.get('email')
        send_type = "resend"
        league_uuid = request.data.get('league_uuid')
        league_secret_key = request.data.get('league_secret_key')

        check_user = IsSponsorDetails.objects.filter(uuid=sponsor_uuid, secret_key=sponsor_secret_key)
        check_league = Leagues.objects.filter(uuid=league_uuid, secret_key=league_secret_key)
        if check_user.exists() and check_league.exists():
            league = check_league.first().name
            #protocol = 'https' if request.is_secure() else 'http'
            host = request.get_host()
            current_site = f"{protocol}://{host}"
            send_email_status = send_email_for_invite_sponsor(current_site, email, league, send_type)
            if send_email_status is True:
                data['status'], data['message'] = status.HTTP_200_OK, "Send Email successfully"
            else:
                data['status'], data['message'] = status.HTTP_404_NOT_FOUND, f"Somthing is wrong"
        else:
            data['status'], data['message'] = status.HTTP_404_NOT_FOUND, "Sponsor or league not found"
    except Exception as e:
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, str(e)
    
    return Response(data)


@api_view(('GET',))
def list_leagues_for_sponsor(request):
    data = {'status':'','data':'','message':''}
    try:        
        user_uuid = request.GET.get('user_uuid')
        user_secret_key = request.GET.get('user_secret_key')
        filter_by = request.GET.get('filter_by')
        search_text = request.GET.get('search_text')
        '''
        registration_open, future, past
        '''
        check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
        if check_user.first().is_organizer:
            leagues = []
            if search_text:
                all_leagues = Leagues.objects.filter(is_created=True).filter(created_by=check_user.first()).filter(Q(name__icontains=search_text))
            else:
                all_leagues = Leagues.objects.filter(is_created=True).filter(created_by=check_user.first())
            today_date = datetime.now()
            if filter_by == "future" :
                all_leagues = all_leagues.filter(registration_start_date__date__gte=today_date).order_by('-id')
            elif filter_by == "past" :
                all_leagues = all_leagues.filter(registration_end_date__date__lte=today_date).order_by('-id')
            elif filter_by == "registration_open" :
                all_leagues = all_leagues.filter(registration_start_date__date__lte=today_date,registration_end_date__date__gte=today_date).order_by('-id')
            
            elif filter_by == "registration_open_date" :
                all_leagues = all_leagues.filter(registration_start_date__date__lte=today_date,registration_end_date__date__gte=today_date).order_by("leagues_start_date")
            elif filter_by == "registration_open_name" :
                all_leagues = all_leagues.filter(registration_start_date__date__lte=today_date,registration_end_date__date__gte=today_date).order_by("name")
            elif filter_by == "registration_open_city" :
                all_leagues = all_leagues.filter(registration_start_date__date__lte=today_date,registration_end_date__date__gte=today_date).order_by("city")
            elif filter_by == "registration_open_state" :
                all_leagues = all_leagues.filter(registration_start_date__date__lte=today_date,registration_end_date__date__gte=today_date).order_by("state")
            elif filter_by == "registration_open_country" :
                all_leagues = all_leagues.filter(registration_start_date__date__lte=today_date,registration_end_date__date__gte=today_date).order_by("country")
            
            else:
                all_leagues = all_leagues
            leagues = all_leagues.values('uuid','secret_key','name','location','leagues_start_date','leagues_end_date',
                               'registration_start_date','registration_end_date','team_type__name','team_person__name','any_rank','start_rank','end_rank',
                               "street","city","state","postal_code","country","complete_address","latitude","longitude")
            if len(leagues) == 0:
                data["status"], data['data'], data["message"] = status.HTTP_200_OK, leagues, "You have no create Tournament"
            else:
                data["status"], data['data'], data["message"] = status.HTTP_200_OK, leagues, "League data"
        else:
            data["status"], data['data'], data["message"] = status.HTTP_404_NOT_FOUND, "","User not found."
    except Exception as e :
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
    return Response(data)


@api_view(('GET',))
def tournament_schedule(request):
    data = {'status':'','data':[], 'message':''}
    try:
        user_uuid = request.GET.get('user_uuid')
        user_secret_key = request.GET.get('user_secret_key')
        check_user = User.objects.filter(secret_key=user_secret_key,uuid=user_uuid)
        today_date = timezone.now()
        # print(check_user)
        if check_user.exists():
            get_user = check_user.first()
            all_leagues = Leagues.objects.exclude(registration_end_date__date__lte=today_date)
            
            if get_user.is_coach is True or get_user.is_team_manager is True or get_user.is_player is True or get_user.is_organizer is True:
                all_leagues_for_join = all_leagues.filter(registered_team__created_by=get_user).values('uuid','secret_key','name','location','leagues_start_date','leagues_end_date',
                               'registration_start_date','registration_end_date','team_type__name','team_person__name',
                               "street","city","state","postal_code","country","complete_address","latitude","longitude")
                save_leagues = SaveLeagues.objects.filter(created_by=get_user).values("ch_league_id")
                leagues_ids = [i["ch_league_id"] for i in save_leagues]
                all_leagues_for_save = all_leagues.filter(id__in=leagues_ids).values('uuid','secret_key','name','location','leagues_start_date','leagues_end_date',
                               'registration_start_date','registration_end_date','team_type__name','team_person__name',
                               "street","city","state","postal_code","country","complete_address","latitude","longitude")
                all_created_leagues = Leagues.objects.exclude(registration_end_date__date__lte=today_date).filter(created_by=get_user).values('uuid','secret_key','name','location','leagues_start_date','leagues_end_date',
                               'registration_start_date','registration_end_date','team_type__name','team_person__name',
                               "street","city","state","postal_code","country","complete_address","latitude","longitude")
                
                for i in all_created_leagues:
                    i["league_for"] = "Tournament Create"
                for k in all_leagues_for_save:
                    k["league_for"] = "Tournament Saved"
                for l in all_leagues_for_join:
                    l["league_for"] = "Tournament Joined"
                my_all_schedule = list(all_created_leagues)+list(all_leagues_for_save)+list(all_leagues_for_join)
                output = {}
                output_list = []
                for item in my_all_schedule:
                    key = (item["name"])
                    league_for = item["league_for"]
                    if key in output:
                        output[key].append(league_for)
                    else:
                        output[key] = [league_for]
                for key in output:
                    output[key] = ",".join(sorted(set(output[key])))
                    counter = 0
                    for k in my_all_schedule:
                        if k["name"] == key and counter==0:
                            k["league_for"] = output[key]
                            output_list.append(k)
                            counter += 1
                        if counter != 0:
                            break
                print(output_list)
                data['status'], data['data'], data['message'] = status.HTTP_200_OK, output_list, f"Data found"
            else:
                data['status'], data['data'], data['message'] = status.HTTP_200_OK, output_list, f"you have no schedule"
        else:
            data['status'], data['data'], data['message'] = status.HTTP_400_BAD_REQUEST, [], f"user not found"
    except Exception as e :
        data['status'], data['data'], data['message'] = status.HTTP_400_BAD_REQUEST, [], f"{e}"
    return Response(data)         


@api_view(('GET',))
def get_organizer_details(request):
    data = {'status':'', 'message':''}
    try:        
        user_uuid = request.GET.get('user_uuid')
        user_secret_key = request.GET.get('user_secret_key')
        check_user = User.objects.filter(uuid=user_uuid, secret_key=user_secret_key)
        if check_user.exists():
            get_user = check_user.first()
            if get_user.is_admin or get_user.is_organizer:
                data['data'] = list(User.objects.filter(is_organizer=True).values('id','uuid','secret_key','username','first_name','last_name','email','phone','gender','user_birthday','role','rank','image','street','city','state','country','postal_code'))
                data['message'] = "Data found"
                data['status'] = status.HTTP_200_OK
            else:
                data['status'] = status.HTTP_404_NOT_FOUND
                data['message'] = "User is not an organizer or admin"
        else:
            data['status'] = status.HTTP_404_NOT_FOUND
            data['message'] = "User not found."
        return Response(data)
    except Exception as e:
        data['status'] = status.HTTP_400_BAD_REQUEST
        data['message'] = f"{e}"
    return Response(data)
 

@api_view(('GET',))
def get_sponsor_details(request):
    data = {'status':'', 'message':''}
    try:        
        user_uuid = request.GET.get('user_uuid')
        user_secret_key = request.GET.get('user_secret_key')
        check_user = User.objects.filter(uuid=user_uuid, secret_key=user_secret_key)
        if check_user.exists():
            get_user = check_user.first()
            if get_user.is_admin == True:
                data['data'] = list(User.objects.filter(is_sponsor=True).values('uuid','secret_key','username','first_name','last_name','email','phone','gender','user_birthday','role','rank','image','street','city','state','country','postal_code','fb_link','twitter_link','youtube_link','instagram_link'))
                data['message'] = "Data found"
                data['status'] = status.HTTP_200_OK
            else:
                data['status'] = status.HTTP_404_NOT_FOUND
                data['message'] = "User is not a sponsor"
        else:
            data['status'] = status.HTTP_404_NOT_FOUND
            data['message'] = "User not found."
        return Response(data)
    except Exception as e:
        data['status'] = status.HTTP_400_BAD_REQUEST
        data['message'] = f"{e}"
    return Response(data)


@api_view(('GET',))
def get_admin_details(request):
    data = {'status':'', 'message':''}
    try:        
        user_uuid = request.GET.get('user_uuid')
        user_secret_key = request.GET.get('user_secret_key')
        check_user = User.objects.filter(uuid=user_uuid, secret_key=user_secret_key)
        if check_user.exists():
            get_user = check_user.first()
            if get_user.is_admin == True:
                data['data'] = list(User.objects.filter(is_admin=True).values('uuid','secret_key','username','first_name','last_name','email','phone','gender','user_birthday','role','rank','image','street','city','state','country','postal_code','fb_link','twitter_link','youtube_link','instagram_link'))
                data['message'] = "Data found"
                data['status'] = status.HTTP_200_OK
            else:
                data['status'] = status.HTTP_404_NOT_FOUND
                data['message'] = "User is not admin."
        else:
            data['status'] = status.HTTP_404_NOT_FOUND
            data['message'] = "User not found."
        return Response(data)
    except Exception as e:
        data['status'] = status.HTTP_400_BAD_REQUEST
        data['message'] = f"{e}"
    return Response(data)


@api_view(('GET',))
def get_ambassador_details(request):
    data = {'status':'', 'message':''}
    try:        
        user_uuid = request.GET.get('user_uuid')
        user_secret_key = request.GET.get('user_secret_key')
        check_user = User.objects.filter(uuid=user_uuid, secret_key=user_secret_key)
        if check_user.exists():
            get_user = check_user.first()
            if get_user.is_admin == True:
                data['data'] = list(User.objects.filter(is_ambassador=True).values('uuid','secret_key','username','first_name','last_name','email','phone','gender','user_birthday','role','rank','image','street','city','state','country','postal_code','fb_link','twitter_link','youtube_link','instagram_link'))
                data['message'] = "Data found"
                data['status'] = status.HTTP_200_OK
            else:
                data['status'] = status.HTTP_404_NOT_FOUND
                data['message'] = "User is not an ambassador."
        else:
            data['status'] = status.HTTP_404_NOT_FOUND
            data['message'] = "User not found."
        return Response(data)
    except Exception as e:
        data['status'] = status.HTTP_400_BAD_REQUEST
        data['message'] = f"{e}"
    return Response(data)


@api_view(('POST',))
def remove_organizer(request):
    data = {'status':'', 'message':''}
    try:        
        user_uuid = request.POST.get('user_uuid')
        user_secret_key = request.POST.get('user_secret_key')
        r_uuid = request.POST.get('r_uuid')
        r_secret_key = request.POST.get('r_secret_key')
        check_user = User.objects.filter(uuid=user_uuid, secret_key=user_secret_key)
        r_user = User.objects.filter(uuid=r_uuid, secret_key=r_secret_key)
        if check_user.exists() and r_user.exists() and check_user.first().is_admin:
            r_user.update(is_organizer=False)
            data['message'] = "Remove from organizer"
            data['status'] = status.HTTP_200_OK
        else:
            data['status'] = status.HTTP_404_NOT_FOUND
            data['message'] = "User not found."
        return Response(data)
    except Exception as e:
        data['status'] = status.HTTP_400_BAD_REQUEST
        data['message'] = f"{e}"
    return Response(data)

    
@api_view(('POST',))
def remove_sponsor(request):
    data = {'status':'', 'message':''}
    try:        
        user_uuid = request.POST.get('user_uuid')
        user_secret_key = request.POST.get('user_secret_key')
        r_uuid = request.POST.get('r_uuid')
        r_secret_key = request.POST.get('r_secret_key')
        check_user = User.objects.filter(uuid=user_uuid, secret_key=user_secret_key)
        r_user = User.objects.filter(uuid=r_uuid, secret_key=r_secret_key)
        if check_user.exists() and r_user.exists():
            IsSponsorDetails.objects.filter(sponsor=r_user.first()).delete()
            r_user.update(is_sponsor=False, role="",is_verified=False)
            data['message'] = "Remove from Sponsor"
            data['status'] = status.HTTP_200_OK
        else:
            data['status'] = status.HTTP_404_NOT_FOUND
            data['message'] = "User not found."
        return Response(data)
    except Exception as e:
        data['status'] = status.HTTP_400_BAD_REQUEST
        data['message'] = f"{e}"
    return Response(data)


@api_view(('POST',))
def remove_admin(request):
    data = {'status':'', 'message':''}
    try:        
        user_uuid = request.POST.get('user_uuid')
        user_secret_key = request.POST.get('user_secret_key')
        r_uuid = request.POST.get('r_uuid')
        r_secret_key = request.POST.get('r_secret_key')
        check_user = User.objects.filter(uuid=user_uuid, secret_key=user_secret_key)
        r_user = User.objects.filter(uuid=r_uuid, secret_key=r_secret_key)
        if check_user.exists() and r_user.exists() and check_user.first().is_admin:
            r_user.update(is_admin=False)
            data['message'] = "Remove from admin"
            data['status'] = status.HTTP_200_OK
        else:
            data['status'] = status.HTTP_404_NOT_FOUND
            data['message'] = "User not found."
        return Response(data)
    except Exception as e:
        data['status'] = status.HTTP_400_BAD_REQUEST
        data['message'] = f"{e}"
    return Response(data)

    
@api_view(('POST',))
def remove_ambassador(request):
    data = {'status':'', 'message':''}
    try:        
        user_uuid = request.POST.get('user_uuid')
        user_secret_key = request.POST.get('user_secret_key')
        r_uuid = request.POST.get('r_uuid')
        r_secret_key = request.POST.get('r_secret_key')
        check_user = User.objects.filter(uuid=user_uuid, secret_key=user_secret_key)
        r_user = User.objects.filter(uuid=r_uuid, secret_key=r_secret_key)
        if check_user.exists() and r_user.exists() and check_user.first().is_admin:
            r_user.update(is_ambassador=False)
            data['message'] = "Remove from ambassador"
            data['status'] = status.HTTP_200_OK
        else:
            data['status'] = status.HTTP_404_NOT_FOUND
            data['message'] = "User not found."
        return Response(data)
    except Exception as e:
        data['status'] = status.HTTP_400_BAD_REQUEST
        data['message'] = f"{e}"
    return Response(data)



"""
not needed
"""
@api_view(('GET',))
def view_leagues(request):
    data = {
            'status':'',
            'create_group_status':False,
            'max_team': None,
            'total_register_team':None,
            'is_organizer': False,
            'is_register': False,
            'sub_organizer_data':[],
            'organizer_name_data':[],
            'invited_code':None,
            'winner_team': 'Not Declared',
            'data':[],
            'tournament_detais':[],
            'point_table':[],
            'elemination':[], 
            'final':[], 
            'message':'',
            'match':[]
            }
    try:        
        user_uuid = request.GET.get('user_uuid')
        user_secret_key = request.GET.get('user_secret_key')
        league_uuid = request.GET.get('league_uuid')
        league_secret_key = request.GET.get('league_secret_key')
        protocol = 'https' if request.is_secure() else 'http'
        host = request.get_host()
        media_base_url = f"{protocol}://{host}{settings.MEDIA_URL}"
        '''
        registration_open, future, past
        '''
        check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
        check_leagues = Leagues.objects.filter(uuid=league_uuid,secret_key=league_secret_key)
        if check_user.exists() and check_leagues.exists():
            leagues = check_leagues.values('uuid','secret_key','name','location','leagues_start_date','leagues_end_date',
                               'registration_start_date','registration_end_date','team_type__name','team_person__name',
                               "street","city","state","postal_code","country","complete_address","latitude","longitude","play_type","registration_fee","description","image","others_fees", "league_type")
            league = check_leagues.first()
            get_user = check_user.first()

            today_date = datetime.today().date()
            if league.registration_end_date not in [None, "null", "", "None"]:
                if league.registration_end_date.date() >= today_date and league.league_type != "Invites only" and league.max_number_team > league.registered_team.count() and not league.is_complete:
                    data["is_register"] = True
            
            organizers = list(User.objects.filter(id=league.created_by.id).values('id','uuid','secret_key','username','first_name','last_name','email','phone','gender','user_birthday','role','rank','image','street','city','state','country','postal_code'))
            sub_organizer_data = list(league.add_organizer.all().values('id','uuid','secret_key','username','first_name','last_name','email','phone','gender','user_birthday','role','rank','image','street','city','state','country','postal_code'))
            
            organizer_list = organizers + sub_organizer_data
            for nu in organizer_list:
                nu["phone"] = str(nu["phone"])
            data['sub_organizer_data'] = organizer_list
            
            organizer_list = []
            for org in data['sub_organizer_data']:
                first_name = org["first_name"]
                last_name = org["last_name"]
                if not first_name:
                    first_name = " "
                if not last_name:
                    last_name = " "
                name = f"{first_name} {last_name}"
                organizer_list.append(name)
            data['organizer_name_data'] = organizer_list

            orgs = list(User.objects.filter(id=league.created_by.id).values_list('id', flat=True))
            sub_org_list = list(league.add_organizer.all().values_list("id", flat=True))  
            orgs_list = orgs + sub_org_list

            if get_user == league.created_by or get_user.id in sub_org_list:
                data['is_organizer'] =  True
                data['invited_code'] =  league.invited_code
            
            data['max_team'] =  league.max_number_team
            data['total_register_team'] =  league.registered_team.all().count()
            data['tournament_detais'] = LeaguesPlayType.objects.filter(league_for = check_leagues.first()).values()
            data['data'] = leagues

            ######## tournament matches details ########
            #working
            tournament_details = Tournament.objects.filter(leagues=check_leagues.first()).order_by("match_number").values("id","match_number","uuid","secret_key","leagues__name",
                                                                                                                          "team1_id", "team2_id", "team1__team_image", "team2__team_image", 
                                                                                                                          "team1__name", "team2__name", "winner_team_id", "winner_team__name", 
                                                                                                                          "playing_date_time","match_type","group__court","is_completed",
                                                                                                                          "elimination_round","court_sn","set_number","court_num","points","is_drow")
            
            for sc in tournament_details:
                if sc["group__court"] is None:
                    sc["group__court"] = sc["court_sn"]

                team_1_player = list(Player.objects.filter(team__id=sc["team1_id"]).values_list("player_id", flat=True))
                team_2_player = list(Player.objects.filter(team__id=sc["team2_id"]).values_list("player_id", flat=True))
                team_1_created_by = Team.objects.filter(id=sc["team1_id"]).first().created_by
                team_2_created_by = Team.objects.filter(id=sc["team2_id"]).first().created_by

                if (get_user.id in orgs_list) or (get_user.id in team_1_player) or (get_user == team_1_created_by) or (get_user.id in team_2_player) or ((get_user == team_2_created_by)):
                    sc["is_edit"] = True
                else:
                    sc["is_edit"] = False

                check_score_approved = TournamentScoreApproval.objects.filter(tournament__id=sc["id"], team1_approval=True, team2_approval=True, organizer_approval=True)

                if check_score_approved.exists():
                    sc["is_score_approved"] = True
                    sc["is_edit"] = False
                else:
                    sc["is_score_approved"] = False                    
                
                check_score_reported = TournamentScoreReport.objects.filter(tournament__id=sc["id"], status="Pending")
                if check_score_reported.exists():
                    sc["is_score_reported"] = True 
                    if (get_user.id in orgs_list):
                        sc["is_edit"] = True
                    else:
                        sc["is_edit"] = False
                else:
                    sc["is_score_reported"] = False   

                team1_approval = TournamentScoreApproval.objects.filter(tournament__id=sc["id"], team1_approval=True).exists()
                team2_approval = TournamentScoreApproval.objects.filter(tournament__id=sc["id"], team2_approval=True).exists()
                organizer_approval = TournamentScoreApproval.objects.filter(tournament__id=sc["id"], organizer_approval=True).exists()
                check_score_set = TournamentSetsResult.objects.filter(tournament__id=sc["id"])

                if check_score_set.exists() and not team1_approval and ((get_user.id in team_1_player) or (get_user == team_1_created_by)) and not check_score_reported.exists():
                    sc['is_organizer'] = False
                    sc["is_button_show"] = True
                
                elif check_score_set.exists() and not team2_approval and ((get_user.id in team_2_player) or (get_user == team_2_created_by)) and not check_score_reported.exists():
                    sc['is_organizer'] = False
                    sc["is_button_show"] = True
                elif check_score_set.exists() and (get_user.id in organizer_list) and not organizer_approval:
                    sc['is_organizer'] = True
                    sc["is_button_show"] = True
                else:   
                    sc['is_organizer'] = False             
                    sc["is_button_show"] = False

                if sc["team1__team_image"] != "":
                    img_str = sc["team1__team_image"]
                    sc["team1__team_image"] = f"{media_base_url}{img_str}"
                if sc["team2__team_image"] != "":
                    img_str = sc["team2__team_image"]
                    sc["team2__team_image"] = f"{media_base_url}{img_str}"
                #"set_number","court_num","points"
                set_list_team1 = []
                set_list_team2 = []
                score_list_team1 = []
                score_list_team2 = []
                win_status_team1 = []
                win_status_team2 = []
                is_completed_match = sc["is_completed"]
                is_win_match_team1 = False
                is_win_match_team2 = False
                team1_name = sc["team1__name"]
                team2_name = sc["team2__name"]
                if sc["team1_id"] == sc["winner_team_id"] and sc["winner_team_id"] is not None:
                    is_win_match_team1 = True
                    is_win_match_team2 = False
                elif sc["team2_id"] == sc["winner_team_id"] and sc["winner_team_id"] is not None:
                    is_win_match_team2 = True
                    is_win_match_team1 = False
                # else:
                #     is_win_match_team2 = False
                #     is_win_match_team1 = False
                for s in range(sc["set_number"]):
                    index = s+1
                    set_str = f"s{index}"
                    set_list_team1.append(set_str)
                    set_list_team2.append(set_str)
                    score_details_for_set = TournamentSetsResult.objects.filter(tournament_id=sc["id"],set_number=index).values()
                    if len(score_details_for_set)!=0:
                        team_1_score = score_details_for_set[0]["team1_point"]
                        team_2_score = score_details_for_set[0]["team2_point"]
                    else:
                        team_1_score = None
                        team_2_score = None
                    score_list_team1.append(team_1_score)
                    score_list_team2.append(team_2_score)
                    if team_1_score is not None and team_2_score is not None:
                        if team_1_score >= team_2_score:
                            win_status_team1.append(True)
                            win_status_team2.append(False)
                        else:
                            win_status_team1.append(False)
                            win_status_team2.append(True)
                    else:
                        win_status_team1.append(False)
                        win_status_team2.append(False)
                score = [
                    {
                     "name": team1_name,"set": set_list_team2,
                     "score": score_list_team1,"win_status": win_status_team1,
                     "is_win": is_win_match_team1,"is_completed": is_completed_match
                     },
                    {
                    "name": team2_name,"set": set_list_team2,
                    "score": score_list_team2,"win_status": win_status_team1,
                    "is_win": is_win_match_team2,"is_completed": is_completed_match
                    }
                    ]
                sc["score"] = score
                # print(score)
            
              
            data['match'] = tournament_details
            ######## tournament matches details ########

            ########### Knock Out part ####################

            #this data for Elimination Round   
            knock_out_tournament_elimination_data = Tournament.objects.filter(leagues=check_leagues.first(),match_type="Elimination Round").values("id","uuid","secret_key","match_number","match_type","elimination_round","team1__name", "team1_id", "team2_id"
                                                                                                            ,"team1__team_image","team2__name","team2__team_image","winner_team__name", "winner_team_id", "loser_team_id", "winner_team__team_image","loser_team__name","loser_team__team_image","is_completed","play_ground_name")
            for ele_tour in knock_out_tournament_elimination_data:
                # ele_tour["is_edit"] = get_user.is_organizer and check_leagues.first().created_by == get_user or ele_tour["team1_id"] == get_user.id or ele_tour["team2_id"] == get_user.id
                if (get_user.id in orgs_list) or (get_user.id in team_1_player) or (get_user == team_1_created_by) or (get_user.id in team_2_player) or ((get_user == team_2_created_by)):
                    sc["is_edit"] = True
                else:
                    sc["is_edit"] = False

                check_score_approved = TournamentScoreApproval.objects.filter(tournament__id=sc["id"], team1_approval=True, team2_approval=True, organizer_approval=True)

                if check_score_approved.exists():
                    sc["is_score_approved"] = True
                    sc["is_edit"] = False
                else:
                    sc["is_score_approved"] = False                    
                
                check_score_reported = TournamentScoreReport.objects.filter(tournament__id=sc["id"], status="Pending")
                if check_score_reported.exists():
                    sc["is_score_reported"] = True 
                    if (get_user.id in orgs_list):
                        sc["is_edit"] = True
                    else:
                        sc["is_edit"] = False
                else:
                    sc["is_score_reported"] = False   

                team1_approval = TournamentScoreApproval.objects.filter(tournament__id=sc["id"], team1_approval=True).exists()
                team2_approval = TournamentScoreApproval.objects.filter(tournament__id=sc["id"], team2_approval=True).exists()
                organizer_approval = TournamentScoreApproval.objects.filter(tournament__id=sc["id"], organizer_approval=True).exists()
                check_score_set = TournamentSetsResult.objects.filter(tournament__id=sc["id"])

                if check_score_set.exists() and not team1_approval and ((get_user.id in team_1_player) or (get_user == team_1_created_by)) and not check_score_reported.exists():
                    sc['is_organizer'] = False
                    sc["is_button_show"] = True
                
                elif check_score_set.exists() and not team2_approval and ((get_user.id in team_2_player) or (get_user == team_2_created_by)) and not check_score_reported.exists():
                    sc['is_organizer'] = False
                    sc["is_button_show"] = True
                elif check_score_set.exists() and (get_user.id in organizer_list) and not organizer_approval:
                    sc['is_organizer'] = True
                    sc["is_button_show"] = True
                else:   
                    sc['is_organizer'] = False             
                    sc["is_button_show"] = False

                score = [{"name": "","set": [],"score": [],"win_status": [],"is_win": True,"is_completed": True},{"name": "","set": [],"score": [],"win_status": [],"is_win": True,"is_completed": True}]
                
                if ele_tour["team1_id"] == ele_tour["winner_team_id"] and ele_tour["winner_team_id"] is not None:
                    score[0]["is_win"] = True
                    score[1]["is_win"] = False
                elif ele_tour["team2_id"] == ele_tour["winner_team_id"] and ele_tour["winner_team_id"] is not None:
                    score[1]["is_win"] = True
                    score[0]["is_win"] = False
                else:
                    score[1]["is_win"] = None
                    score[0]["is_win"] = None
                score_details = TournamentSetsResult.objects.filter(tournament_id=ele_tour["id"]).values()
                score[0]["name"] = ele_tour["team1__name"]
                score[1]["name"] = ele_tour["team2__name"]
                score[0]["set"] = ["s1","s2","s3"]
                score[1]["set"] = ["s1","s2","s3"]
                for l__ in range(3):
                    
                    if l__ < len(score_details):
                        l = {"team1_point":score_details[l__]["team1_point"],"team2_point":score_details[l__]["team2_point"]}
                    else:
                        l = {"team1_point":None,"team2_point":None}
                    
                    score[0]["score"].append(l["team1_point"])
                    score[1]["score"].append(l["team2_point"])
                    
                    if l["team1_point"] == None or l["team1_point"] == None:
                        score[0]["win_status"].append(None)
                        score[1]["win_status"].append(None)
                    elif l["team1_point"] > l["team2_point"]:
                        score[0]["win_status"].append(True)
                        score[1]["win_status"].append(False)
                    else:
                        score[0]["win_status"].append(False)
                        score[1]["win_status"].append(True)
                ele_tour["score"] = score
            data['elemination'] = list(knock_out_tournament_elimination_data)

            #this data for Semi Final   
            knock_out_semifinal_tournament_data = Tournament.objects.filter(leagues=check_leagues.first(),match_type="Semi Final").values("id","uuid","secret_key","match_number","match_type","elimination_round","team1__name", "team1_id", "team2_id"
                                                                                                            ,"team1__team_image","team2__name","team2__team_image","winner_team__name", "winner_team_id", "loser_team_id", "winner_team__team_image","loser_team__name","loser_team__team_image","is_completed","play_ground_name")
            for semi_tour in knock_out_semifinal_tournament_data:
                if (get_user.id in orgs_list) or (get_user.id in team_1_player) or (get_user == team_1_created_by) or (get_user.id in team_2_player) or ((get_user == team_2_created_by)):
                    sc["is_edit"] = True
                else:
                    sc["is_edit"] = False
                
                check_score_approved = TournamentScoreApproval.objects.filter(tournament__id=sc["id"], team1_approval=True, team2_approval=True, organizer_approval=True)

                if check_score_approved.exists():
                    sc["is_score_approved"] = True
                    sc["is_edit"] = False
                else:
                    sc["is_score_approved"] = False                    
                
                check_score_reported = TournamentScoreReport.objects.filter(tournament__id=sc["id"], status="Pending")
                if check_score_reported.exists():
                    sc["is_score_reported"] = True 
                    if (get_user.id in orgs_list):
                        sc["is_edit"] = True
                    else:
                        sc["is_edit"] = False
                else:
                    sc["is_score_reported"] = False   

                team1_approval = TournamentScoreApproval.objects.filter(tournament__id=sc["id"], team1_approval=True).exists()
                team2_approval = TournamentScoreApproval.objects.filter(tournament__id=sc["id"], team2_approval=True).exists()
                organizer_approval = TournamentScoreApproval.objects.filter(tournament__id=sc["id"], organizer_approval=True).exists()
                check_score_set = TournamentSetsResult.objects.filter(tournament__id=sc["id"])

                if check_score_set.exists() and not team1_approval and ((get_user.id in team_1_player) or (get_user == team_1_created_by)) and not check_score_reported.exists():
                    sc['is_organizer'] = False
                    sc["is_button_show"] = True
                
                elif check_score_set.exists() and not team2_approval and ((get_user.id in team_2_player) or (get_user == team_2_created_by)) and not check_score_reported.exists():
                    sc['is_organizer'] = False
                    sc["is_button_show"] = True
                elif check_score_set.exists() and (get_user.id in organizer_list) and not organizer_approval:
                    sc['is_organizer'] = True
                    sc["is_button_show"] = True
                else:   
                    sc['is_organizer'] = False             
                    sc["is_button_show"] = False

                score = [{"name": "","set": [],"score": [],"win_status": [],"is_win": True,"is_completed": True},{"name": "","set": [],"score": [],"win_status": [],"is_win": True,"is_completed": True}]
                
                if semi_tour["team1_id"] == semi_tour["winner_team_id"] and semi_tour["winner_team_id"] is not None:
                    score[0]["is_win"] = True
                    score[1]["is_win"] = False
                elif semi_tour["team2_id"] == semi_tour["winner_team_id"] and semi_tour["winner_team_id"] is not None:
                    score[1]["is_win"] = True
                    score[0]["is_win"] = False
                else:
                    score[1]["is_win"] = None
                    score[0]["is_win"] = None
                score_details = TournamentSetsResult.objects.filter(tournament_id=semi_tour["id"]).values()
                score[0]["name"] = semi_tour["team1__name"]
                score[1]["name"] = semi_tour["team2__name"]
                score[0]["set"] = ["s1","s2","s3"]
                score[1]["set"] = ["s1","s2","s3"]
                for l__ in range(3):
                    
                    if l__ < len(score_details):
                        l = {"team1_point":score_details[l__]["team1_point"],"team2_point":score_details[l__]["team2_point"]}
                    else:
                        l = {"team1_point":None,"team2_point":None}
                    
                    score[0]["score"].append(l["team1_point"])
                    score[1]["score"].append(l["team2_point"])
                    
                    if l["team1_point"] == None or l["team1_point"] == None:
                        score[0]["win_status"].append(None)
                        score[1]["win_status"].append(None)
                    elif l["team1_point"] > l["team2_point"]:
                        score[0]["win_status"].append(True)
                        score[1]["win_status"].append(False)
                    else:
                        score[0]["win_status"].append(False)
                        score[1]["win_status"].append(True)
                semi_tour["score"] = score
            data['semi_final'] = list(knock_out_semifinal_tournament_data)

            #this data for Final 
            knock_out_final_tournament_data = Tournament.objects.filter(leagues=check_leagues.first(),match_type="Final").values("id","uuid","secret_key","match_number","match_type","elimination_round","team1__name", "team1_id", "team2_id"
                                                                                                            ,"team1__team_image","team2__name","team2__team_image","winner_team__name", "winner_team_id", "loser_team_id", "winner_team__team_image","loser_team__name","loser_team__team_image","is_completed","play_ground_name")
            for final_tour in knock_out_final_tournament_data:
                if (get_user.id in orgs_list) or (get_user.id in team_1_player) or (get_user == team_1_created_by) or (get_user.id in team_2_player) or ((get_user == team_2_created_by)):
                    sc["is_edit"] = True
                else:
                    sc["is_edit"] = False

                check_score_approved = TournamentScoreApproval.objects.filter(tournament__id=sc["id"], team1_approval=True, team2_approval=True)

                if check_score_approved.exists():
                    sc["is_score_approved"] = True
                    sc["is_edit"] = False
                else:
                    sc["is_score_approved"] = False                    
                
                check_score_reported = TournamentScoreReport.objects.filter(tournament__id=sc["id"], status="Pending")
                if check_score_reported.exists():
                    sc["is_score_reported"] = True 
                    if (get_user.id in orgs_list):
                        sc["is_edit"] = True
                    else:
                        sc["is_edit"] = False
                else:
                    sc["is_score_reported"] = False   

                team1_approval = TournamentScoreApproval.objects.filter(tournament__id=sc["id"], team1_approval=True).exists()
                team2_approval = TournamentScoreApproval.objects.filter(tournament__id=sc["id"], team2_approval=True).exists()
                organizer_approval = TournamentScoreApproval.objects.filter(tournament__id=sc["id"], organizer_approval=True).exists()
                check_score_set = TournamentSetsResult.objects.filter(tournament__id=sc["id"])

                if check_score_set.exists() and not team1_approval and ((get_user.id in team_1_player) or (get_user == team_1_created_by)) and not check_score_reported.exists():
                    sc['is_organizer'] = False
                    sc["is_button_show"] = True
                
                elif check_score_set.exists() and not team2_approval and ((get_user.id in team_2_player) or (get_user == team_2_created_by)) and not check_score_reported.exists():
                    sc['is_organizer'] = False
                    sc["is_button_show"] = True
                elif check_score_set.exists() and (get_user.id in organizer_list) and not organizer_approval:
                    sc['is_organizer'] = True
                    sc["is_button_show"] = True
                else:   
                    sc['is_organizer'] = False             
                    sc["is_button_show"] = False

                score = [{"name": "","set": [],"score": [],"win_status": [],"is_win": True,"is_completed": True},{"name": "","set": [],"score": [],"win_status": [],"is_win": True,"is_completed": True}]
                
                if final_tour["team1_id"] == final_tour["winner_team_id"] and final_tour["winner_team_id"] is not None:
                    score[0]["is_win"] = True
                    score[1]["is_win"] = False
                elif final_tour["team2_id"] == final_tour["winner_team_id"] and final_tour["winner_team_id"] is not None:
                    score[1]["is_win"] = True
                    score[0]["is_win"] = False
                else:
                    score[1]["is_win"] = None
                    score[0]["is_win"] = None
                score_details = TournamentSetsResult.objects.filter(tournament_id=final_tour["id"]).values()
                score[0]["name"] = final_tour["team1__name"]
                score[1]["name"] = final_tour["team2__name"]
                score[0]["set"] = ["s1","s2","s3"]
                score[1]["set"] = ["s1","s2","s3"]
                for l__ in range(3):
                    
                    if l__ < len(score_details):
                        l = {"team1_point":score_details[l__]["team1_point"],"team2_point":score_details[l__]["team2_point"]}
                    else:
                        l = {"team1_point":None,"team2_point":None}
                    
                    score[0]["score"].append(l["team1_point"])
                    score[1]["score"].append(l["team2_point"])
                    
                    if l["team1_point"] == None or l["team1_point"] == None:
                        score[0]["win_status"].append(None)
                        score[1]["win_status"].append(None)
                    elif l["team1_point"] > l["team2_point"]:
                        score[0]["win_status"].append(True)
                        score[1]["win_status"].append(False)
                    else:
                        score[0]["win_status"].append(False)
                        score[1]["win_status"].append(True)
                final_tour["score"] = score
            data['final'] = list(knock_out_final_tournament_data)

            ########### Knock Out part ####################
            
            ########### declear winner team and update ##########
            play_type_check_win = league.play_type
            if play_type_check_win == "Group Stage" or play_type_check_win == "Single Elimination":
                check_final = Tournament.objects.filter(leagues=check_leagues.first(),match_type="Final",is_completed=True)
                if check_final.exists():
                    final_match = check_final.first()
                    winner_team = final_match.winner_team
                    winner_team_name = final_match.winner_team.name
                    league.winner_team = winner_team
                    league.is_complete = True
                    league.save()
                    data["winner_team"] = winner_team_name
                else:
                    pass

            else:
                check_final = Tournament.objects.filter(leagues=check_leagues.first(),match_type="Individual Match Play",is_completed=True)
                if check_final.exists():
                    final_match = check_final.first()
                    if not final_match.is_drow:
                        winner_team = final_match.winner_team
                        winner_team_name = final_match.winner_team.name
                        league.winner_team = winner_team
                        league.is_complete = True
                        league.save()
                        data["winner_team"] = winner_team_name
                    else:
                        winner_team1 = final_match.team1
                        winner_team2 = final_match.team2
                        # league.winner_team = None
                        league.is_complete = True
                        league.save()
                        data["winner_team"] = f"{winner_team1.name}, {winner_team2.name}"
                else:
                    pass
            ########### declear winner team and update ##########


            #If Tournament is Group stage or Round Robin
            ############# point table ########################
            all_group_details = RoundRobinGroup.objects.filter(league_for=league)
            for grp in all_group_details:
                teams = grp.all_teams.all()
                group_score_point_table = []
                # print(teams)
                for team in teams:
                    team_score = {}
                    total_match_detals = Tournament.objects.filter(leagues=league, match_type="Round Robin").filter(Q(team1=team) | Q(team2=team))
                    completed_match_details = total_match_detals.filter(is_completed=True)
                    win_match_details = completed_match_details.filter(winner_team=team).count()
                    loss_match_details = completed_match_details.filter(loser_team=team).count()
                    drow_match = len(completed_match_details) - (win_match_details + loss_match_details)
                    match_list = list(total_match_detals.values_list("id", flat=True))
                    for_score = 0
                    aginst_score = 0
                    for sc in match_list:
                        co_team_position = Tournament.objects.filter(id=sc).first()
                        set_score = TournamentSetsResult.objects.filter(tournament_id=sc)
                        if co_team_position.team1 == team:
                           for_score = for_score + sum(list(set_score.values_list("team1_point", flat=True)))
                           aginst_score = aginst_score + sum(list(set_score.values_list("team2_point", flat=True)))
                        else:
                            for_score = for_score + sum(list(set_score.values_list("team2_point", flat=True)))
                            aginst_score = aginst_score + sum(list(set_score.values_list("team1_point", flat=True)))
                    
                    point = (win_match_details * 3) + (drow_match * 1)
                    team_score["uuid"], team_score["secret_key"] = team.uuid, team.secret_key
                    team_score["name"], team_score["completed_match"] = team.name, len(completed_match_details)
                    team_score["win_match"], team_score["loss_match"] = win_match_details, loss_match_details
                    team_score["drow_match"], team_score["for_score"] = drow_match, for_score
                    team_score["aginst_score"], team_score["point"] = aginst_score, point
                    group_score_point_table.append(team_score)
                # Append team details to group data
                tournament_details_group = Tournament.objects.filter(leagues=league,group=grp).values("id","uuid","secret_key","team1__name","team2__name","leagues__name","match_type","is_completed","group__court","play_ground_name","playing_date_time","group_id")
                for k_ in tournament_details_group:
                    round_robin_group_detals = RoundRobinGroup.objects.filter(league_for=league, id=k_["group_id"]).first()
                    k_["sets"] = round_robin_group_detals.number_sets
                    k_["court"] = round_robin_group_detals.court
                    k_["score"] = list(TournamentSetsResult.objects.filter(tournament_id=k_["id"]).values())
                
                group_score_point_table = sorted(group_score_point_table, key=lambda x: (x['point'], x['for_score']), reverse=True)
                # print(group_score_point_table)

                ###### tournament winning team update and declare
                if play_type_check_win == "Round Robin":
                    total_tournament = Tournament.objects.filter(leagues=check_leagues.first(),match_type="Round Robin",leagues__play_type="Round Robin")
                    completed_tournament = total_tournament.filter(is_completed=True)
                    if total_tournament.count() == completed_tournament.count():
                        winner_team = Team.objects.filter(uuid=group_score_point_table[0]["uuid"]).first()
                        winner_team_name = winner_team.name
                        league.winner_team = winner_team
                        league.is_complete = True
                        league.save()
                        data["winner_team"] = winner_team_name
                grp_data = {
                    "id": grp.id,
                    "court": grp.court,
                    "league_for_id": grp.league_for_id,
                    "all_games_status": grp.all_games_status,
                    "all_tems": group_score_point_table,
                    "tournament": tournament_details_group,
                    "seleced_teams_id": grp.seleced_teams_id
                }
                data['point_table'].append(grp_data)

            all_team = check_leagues.first().registered_team.all()
            ############# point table ########################


            ######### Tornament all teams details ############
            teams = []
            for t in all_team:
                team_d = Team.objects.filter(id=t.id).values()
                teams.append(team_d[0])
            for im in teams:
                if im["team_image"] != "":
                    img_str = im["team_image"]
                    im["team_image"] = f"{media_base_url}{img_str}"
            
            data['teams'] = teams
            ######### Tornament all teams details ############
            
            
            data["create_group_status"] = get_user.is_organizer and check_leagues.first().created_by == get_user
            data["status"], data["message"] = status.HTTP_200_OK, "League data"
        else:
            data["status"], data['data'], data["message"] = status.HTTP_404_NOT_FOUND, [],  "User or League not found."
    except Exception as e :
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
    return Response(data)



@api_view(('POST',))
def add_team_to_leagues(request):
    data = {'status':'','data':[],'message':''}
    try:        
        user_uuid = request.data.get('user_uuid')
        user_secret_key = request.data.get('user_secret_key')
        league_uuid = request.data.get('league_uuid')
        league_secret_key = request.data.get('league_secret_key')
        team_uuid_all = request.data.get('team_uuid')
        team_secret_key_all = request.data.get('team_secret_key')       
     
        check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
        chaek_leagues = Leagues.objects.filter(uuid=league_uuid,secret_key=league_secret_key)
        if not check_user.exists() and not chaek_leagues.exists():
            data['status'] = status.HTTP_400_BAD_REQUEST
            data['message'] =  f"User or Tournament not found"
            return Response(data)
        
        get_league = chaek_leagues.first()      

        total_registered_teams = get_league.registered_team.all().count()
        today_date = timezone.now()
        if get_league.registration_end_date < today_date or get_league.max_number_team == total_registered_teams or get_league.is_complete == True:
            data['status'] = status.HTTP_400_BAD_REQUEST
            data['message'] =  f"Registration is over."
            return Response(data)
        
        user_id = check_user.first().id
        tournament_id = chaek_leagues.first().id
        team_uuid_all = str(team_uuid_all).split(",")
        team_secret_key_all = str(team_secret_key_all).split(",")
        all_team_id = []
        for t in range(len(team_uuid_all)):
            team = Team.objects.filter(uuid=team_uuid_all[t],secret_key=team_secret_key_all[t])
            if team.exists():
                team_id = team.first().id
                all_team_id.append(team_id)

        if get_league.start_rank and get_league.end_rank:
            for id in all_team_id: 
                team = Team.objects.filter(id=id).values().first()              
                players = Player.objects.filter(team__id=team["id"])
                team_rank = 0
                for player in players:
                    if player.player.rank == "0" or player.player.rank in [0,"", "null", None]:
                        # player.player_ranking = 1.0
                        team_rank += 1
                    else:
                        team_rank += float(player.player.rank)
                team_rank = team_rank / len(players)
                team["rank"] = team_rank
                if not get_league.start_rank<=team["rank"]<=get_league.end_rank:
                    data['status'] = status.HTTP_400_BAD_REQUEST
                    data['message'] =  f"{team['name']} does not have the desired rank."
                    return Response(data)
        #parse_json data
        make_request_data = {"tournament_id":tournament_id,"user_id":user_id,"team_id_list":all_team_id}
        
        #json bytes
        json_bytes = json.dumps(make_request_data).encode('utf-8')
        
        # Encode bytes to base64
        my_data = base64.b64encode(json_bytes).decode('utf-8')

        if check_user.exists() and chaek_leagues.exists():
            number_of_team_join = len(all_team_id)
            get_le = chaek_leagues.first()
            oth = get_le.others_fees
            try:
                others_total = sum(oth.values()) if oth else 0
            except TypeError:
                others_total = 0
            total_ammount = get_le.registration_fee + others_total
            chage_amount =  total_ammount * 100 * number_of_team_join
             
            product_name = "Payment For Register Team"
            product_description = "Payment received by Pickleit"
            stripe.api_key = settings.STRIPE_SECRET_KEY
            get_user = check_user.first()
            if get_user.stripe_customer_id :
                stripe_customer_id = get_user.stripe_customer_id
            else:
                customer = stripe.Customer.create(email=get_user.email).to_dict()
                stripe_customer_id = customer["id"]
                get_user.stripe_customer_id = stripe_customer_id
                get_user.save()
            
            # current_site = request.META['wsgi.url_scheme'] + '://' + request.META['HTTP_HOST']
            #protocol = 'https' if request.is_secure() else 'http'
            host = request.get_host()
            current_site = f"{protocol}://{host}"
            main_url = f"{current_site}/team/c80e2caf03546f11a39db8703fb7f7457afc5cb20db68b5701497fd992a0c29f/{chage_amount}/{my_data}/"
            product = stripe.Product.create(name=product_name,description=product_description,).to_dict()
            price = stripe.Price.create(unit_amount=chage_amount,currency='usd',product=product["id"],).to_dict()
            checkout_session = stripe.checkout.Session.create(
                customer=stripe_customer_id,
                line_items=[
                    {
                        # Provide the exact Price ID (for example, pr_1234) of the product you want to sell
                        'price': price["id"],
                        'quantity': 1,
                    },
                ],
                mode='payment',
                success_url= main_url + "{CHECKOUT_SESSION_ID}" + "/",
                cancel_url="https://example.com/success" + '/cancel.html',
            )
            return Response({"strip_url":checkout_session.url})
    except Exception as e :
        data['status'] = status.HTTP_400_BAD_REQUEST
        data['message'] =  f"{e}"
        return Response(data)

def payment_for_team_registration(request,charge_for,my_data,checkout_session_id):
    try:
        context ={}
        stripe.api_key = settings.STRIPE_SECRET_KEY
        # context['stripe_api_key'] = settings.STRIPE_PUBLIC_KEY
        pay = stripe.checkout.Session.retrieve(checkout_session_id).to_dict()    
        stripe_customer_id = pay["customer"]
        payment_status = pay["payment_status"]
        expires_at = pay["expires_at"]
        amount_total = float(pay["amount_total"]) / 100
        payment_method_types = pay["payment_method_types"]
        payment_status = True if payment_status == "paid" else False
        json_bytes = base64.b64decode(my_data)
        request_data = json.loads(json_bytes.decode('utf-8'))
        # store payment details
        # demo data forment
        """
        {'tournament_id': 112, 'user_id': 3, 'team_id_list': [3]}
        """
        teams_list = list(request_data["team_id_list"])
        teams_count = len(request_data["team_id_list"])
        payment_for = f"Register {teams_count} Team"
        check_tournament = Leagues.objects.filter(id=request_data["tournament_id"]).first()
        payment = PaymentDetailsForRegister(
            tournament=check_tournament,
            payment_for=payment_for,
            payment_by_id=request_data["user_id"],
            charge_amount=amount_total,
            teams_ids={"team_ids":request_data["team_id_list"]},
            payment_status=payment_status
        )
        payment.save()
        if payment_status is True:
            check_tournament.registered_team.add(*teams_list)
            return render(request,"success_payment_for_register_team.html")
        else: 
            return render(request,"failed_paymentregister_team.html")
    except:
        return render(request,"failed_paymentregister_team.html")


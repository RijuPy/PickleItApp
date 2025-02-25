
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from apps.user.models import *
from apps.team.models import *
from apps.user.helpers import *
from apps.team.serializers import *
from apps.pickleitcollection.models import *
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache
from django.contrib.auth.hashers import make_password 
from django.db.models.functions import TruncMonth
from django.db.models import Count,Q, Case, When, IntegerField
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.pagination import PageNumberPagination



"""
player list all user can show the player list
search player / filter player
add cashing in this player lis
"""
@api_view(['GET'])
def player_list_using_pagination(request):
    data = {'status': '', 'count': '', 'previous': '', 'next': '', 'data': [], 'message': ''}
    try:
        user_uuid = request.GET.get('user_uuid')
        user_secret_key = request.GET.get('user_secret_key')
        search_text = request.GET.get('search_text')
        ordering = request.GET.get('ordering')
        gender = request.GET.get('gender')        
        start_rank = request.GET.get('start_rank')
        end_rank = request.GET.get('end_rank')

        check_user = User.objects.filter(uuid=user_uuid, secret_key=user_secret_key)
        if check_user.exists():
            get_user = check_user.first()
            if not search_text:
                all_players = Player.objects.all()
            else:
                all_players = Player.objects.filter(Q(player_first_name__icontains=search_text) | Q(player_last_name__icontains=search_text))

            following = AmbassadorsDetails.objects.filter(ambassador=get_user)
            if following.exists():
                following_instance = following.first()
                following_ids = list(following_instance.following.all().values_list("id", flat=True))
            else:
                following_instance = AmbassadorsDetails.objects.create(ambassador=get_user)
                following_instance.save()
                following_ids = list(following_instance.following.all().values_list("id", flat=True))

            if ordering == 'latest':
                all_players = all_players.order_by('-id')  # Order by latest ID
            elif ordering == 'a-z':
                all_players = all_players.order_by('player_first_name') 
            else:
                all_players = all_players.order_by('-id')

            if gender not in [None, "null", "", "None"]:
                all_players = all_players.filter(player__gender__iexact=gender).order_by("-id")

            if start_rank not in [None, "null", "", "None"] and end_rank not in [None, "null", "", "None"]:
                all_players = all_players.filter(player__rank__gte=start_rank, player__rank__lte=end_rank).order_by("-id")

            #cache implementation
            if not search_text and not ordering:
                players_list = f'player_list'
                if cache.get(players_list):
                    players = cache.get(players_list)
                else:
                    players = all_players
                    cache.set(players_list, players)
            elif search_text and not ordering:
                search_list = f'{search_text}'
                if cache.get(search_list):
                    players = cache.get(search_list)
                else:
                    players = all_players
                    cache.set(search_list, players)

            elif not search_text and ordering:
                ordered_list = f'{ordering}'
                if cache.get(ordered_list):
                    players = cache.get(ordered_list)
                else:
                    players = all_players
                    cache.set(ordered_list, players)
            else:
                cache_key = f'player_list_{search_text}_{ordering}'
                if cache.get(cache_key):
                    players = cache.get(cache_key)
                else:
                    players = all_players
                    cache.set(cache_key, players)
                    
            paginator = PageNumberPagination()
            paginator.page_size = 10  # Set the page size to 20
            result_page = paginator.paginate_queryset(all_players, request)
            serializer = PlayerSerializer(result_page, many=True, context={'request': request})
            serialized_data = serializer.data
            
            def add_additional_fields(player_data):
                player_data["is_edit"] = player_data["created_by_id"] == get_user.id
                player_data["is_follow"] = player_data["player_id"] in following_ids
                return player_data

            serialized_data = list(map(add_additional_fields, serialized_data))
                

            if not serialized_data:
                data["status"] = status.HTTP_200_OK
                data["count"] = 0
                data["previous"] = None
                data["next"] = None
                data["data"] = []
                data["message"] = "No Result found"
            else:
                paginated_response = paginator.get_paginated_response(serialized_data)
                data["status"] = status.HTTP_200_OK
                data["count"] = paginated_response.data["count"]
                data["previous"] = paginated_response.data["previous"]
                data["next"] = paginated_response.data["next"]
                data["data"] = paginated_response.data["results"]
                data["message"] = "Data found"
        else:
            data["count"] = 0
            data["previous"] = None
            data["next"] = None
            data["data"] = []
            data['status'] = status.HTTP_401_UNAUTHORIZED
            data['message'] = "Unauthorized access"

    except Exception as e:
        data["count"] = 0
        data["previous"] = None
        data["next"] = None
        data["data"] = []
        data['status'] = status.HTTP_200_OK
        data['message'] = str(e)

    return Response(data)


"""
show the user own(created player) player list
"""
@api_view(("GET",))
def my_player_list(request):
    data = {'status': '', 'count': '', 'previous': '', 'next': '', 'data': [], 'message': ''}
    try:
        user_uuid = request.GET.get('user_uuid')
        user_secret_key = request.GET.get('user_secret_key')
        search_text = request.GET.get('search_text')
        ordering = request.GET.get('ordering')
        gender = request.GET.get('gender')        
        start_rank = request.GET.get('start_rank')
        end_rank = request.GET.get('end_rank')

        check_user = User.objects.filter(uuid=user_uuid, secret_key=user_secret_key)
        if check_user.exists():
            get_user = check_user.first()
            my_players = Player.objects.filter(created_by_id=get_user.id)
            if not search_text:
                my_players = my_players
            else:
                my_players = my_players.filter(Q(player_first_name__icontains=search_text) | Q(player_last_name__icontains=search_text))

            following = AmbassadorsDetails.objects.filter(ambassador=get_user)
            if following.exists():
                following_instance = following.first()
                following_ids = list(following_instance.following.all().values_list("id", flat=True))
            else:
                following_instance = AmbassadorsDetails.objects.create(ambassador=get_user)
                following_instance.save()
                following_ids = list(following_instance.following.all().values_list("id", flat=True))

            if ordering == 'latest':
                my_players = my_players.order_by('-id')  # Order by latest ID
            elif ordering == 'a-z':
                my_players = my_players.order_by('player_first_name') 
            else:
                my_players = my_players.order_by('-id')

            if gender not in [None, "null", "", "None"]:
                my_players = my_players.filter(player__gender__iexact=gender).order_by("-id")

            if start_rank not in [None, "null", "", "None"] and end_rank not in [None, "null", "", "None"]:
                my_players = my_players.filter(player__rank__gte=start_rank, player__rank__lte=end_rank).order_by("-id")

            #cache implementation
            if not search_text and not ordering:
                players_list = f'player_list'
                if cache.get(players_list):
                    players = cache.get(players_list)
                else:
                    players = my_players
                    cache.set(players_list, players)
            elif search_text and not ordering:
                search_list = f'{search_text}'
                if cache.get(search_list):
                    players = cache.get(search_list)
                else:
                    players = my_players
                    cache.set(search_list, players)

            elif not search_text and ordering:
                ordered_list = f'{ordering}'
                if cache.get(ordered_list):
                    players = cache.get(ordered_list)
                else:
                    players = my_players
                    cache.set(ordered_list, players)
            else:
                cache_key = f'player_list_{search_text}_{ordering}'
                if cache.get(cache_key):
                    players = cache.get(cache_key)
                else:
                    players = my_players
                    cache.set(cache_key, players)

            paginator = PageNumberPagination()
            paginator.page_size = 10  # Set the page size to 20
            result_page = paginator.paginate_queryset(my_players, request)
            serializer = PlayerSerializer(result_page, many=True, context={'request': request})
            serialized_data = serializer.data
            
            def add_additional_fields(player_data):
                player_data["is_edit"] = player_data["created_by_id"] == get_user.id
                player_data["is_follow"] = player_data["player_id"] in following_ids
                return player_data

            serialized_data = list(map(add_additional_fields, serialized_data))
                
            if not serialized_data:
                data["status"] = status.HTTP_200_OK
                data["count"] = 0
                data["previous"] = None
                data["next"] = None
                data["data"] = []
                data["message"] = "No Result found"
            else:
                paginated_response = paginator.get_paginated_response(serialized_data)
                data["status"] = status.HTTP_200_OK
                data["count"] = paginated_response.data["count"]
                data["previous"] = paginated_response.data["previous"]
                data["next"] = paginated_response.data["next"]
                data["data"] = paginated_response.data["results"]
                data["message"] = "Data found"
        else:
            data["count"] = 0
            data["previous"] = None
            data["next"] = None
            data["data"] = []
            data['status'] = status.HTTP_401_UNAUTHORIZED
            data['message'] = "Unauthorized access"

    except Exception as e:
        data["count"] = 0
        data["previous"] = None
        data["next"] = None
        data["data"] = []
        data['status'] = status.HTTP_200_OK
        data['message'] = str(e)

    return Response(data)


"""
create player api
user recived the email with pickleit side link and credancial
"""
@api_view(('POST',))
def create_player(request):
    data = {'status':'','message':''}
    try:        
        user_uuid = request.data.get('user_uuid')
        user_secret_key = request.data.get('user_secret_key')
        p_first_name = request.data.get('p_first_name')
        p_last_name = request.data.get('p_last_name')
        p_email = request.data.get('p_email')
        p_phone_number = request.data.get('p_phone_number')
        p_ranking = request.data.get('p_ranking')
        p_gender = request.data.get('p_gender')
        p_image = request.FILES.get('p_image')
        

        check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
        if check_user.exists() :
            check_player = User.objects.filter(email=p_email)
            if check_player.exists():
                data["status"], data["data"], data["message"] = status.HTTP_200_OK, [],"Player already exists in app"
            get_user = check_user.first()
            obj = GenerateKey()
            secret_key = obj.gen_player_key()
            player_full_name = f"{p_first_name} {p_last_name}"
            identify_player = f"{str(p_first_name)[0]} {str(p_last_name)[0]}"
            role = Role.objects.filter(role="User")
            if not role.exists():
                data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, "player role not exists"
                return Response(data)
            six_digit_number = str(random.randint(100000, 999999))
            # print(six_digit_number)
            save_player = Player(secret_key=secret_key,player_first_name=p_first_name,player_last_name=p_last_name,
                                 player_full_name=player_full_name,player_email=p_email,player_phone_number=p_phone_number,
                                 player_ranking=p_ranking,identify_player=identify_player,created_by=get_user, player_image=p_image)
            
            user_secret_key = obj.gen_user_key()
            user = User.objects.create(secret_key=user_secret_key,phone=p_phone_number,first_name=p_first_name, last_name=p_last_name, username=p_email,email=p_email, password=make_password(six_digit_number), password_raw=six_digit_number, is_player=True,role_id=role.first().id,is_verified=True,image=p_image,
                                rank=p_ranking, gender=p_gender) 
            save_player.player = user
            save_player.save()
            if cache.has_key("player_list"):
                cache.delete("player_list")
            app_name = "PICKLEit"
            login_link = "#"
            password = six_digit_number
            # app_image = "http://18.190.217.171/static/images/PickleIt_logo.png"
            send_email_this_user = send_email_for_invite_player(p_first_name, p_email, app_name, login_link, password)
            # print(send_email_this_user)
            if get_user.is_admin :
                pass
            else:
                get_user.is_team_manager = True
                get_user.is_coach = True
                get_user.save()
            data["status"], data["data"], data["message"] = status.HTTP_200_OK, [],"Player created successfully"
        else:
            data["status"], data["data"], data["message"] = status.HTTP_404_NOT_FOUND, [],"User not found."
    except Exception as e :
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
        
    return Response(data)

"""
player view api
any use can view the player
"""
@api_view(('GET',))
def view_player(request):
    data = {'status':'','message':''}
    try:        
        user_uuid = request.GET.get('user_uuid')
        user_secret_key = request.GET.get('user_secret_key')
        player_uuid = request.GET.get('player_uuid')
        player_secret_key = request.GET.get('player_secret_key')
        check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
        if check_user.exists() :
            check_player = Player.objects.filter(uuid=player_uuid,secret_key=player_secret_key)
            check_player = Player.objects.filter(uuid=player_uuid,secret_key=player_secret_key)
            if check_player.exists():
                get_player = check_player.first()
                get_team = get_player.team.all()
                team_details = []
                if get_team :
                    for i in get_team :
                        team_details.append({"team_id":i.id,"team_name":i.name})

                data["data"] = {"palyer_data":check_player.values("player__first_name","player__last_name","player_ranking","player__rank","player__gender","player__image","player__email","player__phone"),
                                "team_details":team_details}
      
                data["status"], data["message"] = status.HTTP_200_OK, "Data found"
            else:
                data["status"], data["data"], data["message"] = status.HTTP_403_FORBIDDEN, "","Player not found"
        else:
            data["status"], data["message"] = status.HTTP_404_NOT_FOUND, "User not found"  
    except Exception as e :
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
        
    return Response(data)


"""
player profile details api
any use can view the player profile details
"""
@api_view(("GET",))
def player_profile_details(request):
    data = {'status':'','message':''}
    try:        
        user_uuid = request.GET.get('user_uuid')
        user_secret_key = request.GET.get('user_secret_key')
        player_uuid = request.GET.get('player_uuid')
        player_secret_key = request.GET.get('player_secret_key')
        check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
        if check_user.exists() :
            check_player = Player.objects.filter(uuid=player_uuid,secret_key=player_secret_key)
            if check_player:
                player = check_player.first()
                player_data = check_player.values("id", "player__first_name","player__last_name","player__email","player__rank","player__gender","player__phone","player__image","player__bio")
                check_ambassador = AmbassadorsDetails.objects.filter(ambassador=player.player)
                if check_ambassador:
                    follower_count = check_ambassador.first().follower.count()
                    following_count = check_ambassador.first().following.count()
                    is_follow = True if check_user.first() in check_ambassador.first().follower.all() else False
                    posts = AmbassadorsPost.objects.filter(created_by=player.player)
                    post_count = posts.count()
                    post_data = posts.values()
                else:
                    is_follow = False
                    follower_count = 0
                    following_count = 0
                    post_count = 0
                    post_data = []
                ambassador_data = {"follower":follower_count,
                                  "following":following_count,
                                  "is_follow":is_follow,
                                  "posts":post_count,
                                  "post_data":post_data}
                data['status'] = status.HTTP_200_OK
                data['player_data'] = player_data
                data['ambassador_data'] = ambassador_data
                data['message'] = f'Data fetched successfully.'
            else:
                data['status'] = status.HTTP_404_NOT_FOUND
                data['player_data'] = []
                data['ambassador_data'] = []
                data['message'] = f'User is not a player'
        else:
            data['status'] = status.HTTP_404_NOT_FOUND
            data['player_data'] = []
            data['ambassador_data'] = []
            data['message'] = f'User not found'
    except Exception as e:
        data['status'] = status.HTTP_400_BAD_REQUEST
        data['player_data'] = []
        data['ambassador_data'] = []
        data['message'] = f'{str(e)}'
    return Response(data)


"""
player team details api
any use can view the player team details
"""
@api_view(("GET",))
def player_team_details(request):
    data = {'status':'','message':''}
    try:        
        user_uuid = request.GET.get('user_uuid')
        user_secret_key = request.GET.get('user_secret_key')
        player_uuid = request.GET.get('player_uuid')
        player_secret_key = request.GET.get('player_secret_key')
        check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
        if check_user.exists() :
            user = check_user.first()
            check_player = Player.objects.filter(uuid=player_uuid,secret_key=player_secret_key)
            if check_player:
                player = check_player.first()
                team_details = player.team.all()
                paginator = PageNumberPagination()
                paginator.page_size = 20
                paginated_teams = paginator.paginate_queryset(team_details, request)
                serializer  = TeamListSerializer(paginated_teams, many=True)
                main_data = serializer.data
                for team_data in main_data:
                    team_data['is_edit'] = team_data['created_by_uuid'] == user.uuid
                paginated_response = paginator.get_paginated_response(main_data)

                data['status'] = status.HTTP_200_OK
                data["count"] = paginated_response.data["count"]
                data["previous"] = paginated_response.data["previous"]
                data["next"] = paginated_response.data["next"]
                data['team_data'] = paginated_response.data["results"]
                data['message'] = f'Team details fetched successfully.'
            else:
                data['status'] = status.HTTP_404_NOT_FOUND
                data["count"] = 0
                data["previous"] = None
                data["next"] = None
                data['team_data'] = []
                data['message'] = f'User is not a player.' 
        else:
            data['status'] = status.HTTP_404_NOT_FOUND
            data["count"] = 0
            data["previous"] = None
            data["next"] = None
            data['team_data'] = []
            data['message'] = f'User not found.'
    except Exception as e:
        data['status'] = status.HTTP_400_BAD_REQUEST
        data["count"] = 0
        data["previous"] = None
        data["next"] = None
        data['team_data'] = []
        data['message'] = f'{str(e)}'
    return Response(data)  

"""
player stats details api
any use can view the player stats
"""
@api_view(("GET",))
def player_match_statistics(request):
    data = {'status': '', 'message': ''}
    try:        
        user_uuid = request.GET.get('user_uuid')
        user_secret_key = request.GET.get('user_secret_key')
        player_uuid = request.GET.get('player_uuid')
        player_secret_key = request.GET.get('player_secret_key')

        check_user = User.objects.filter(uuid=user_uuid, secret_key=user_secret_key)
        if check_user.exists():
            check_player = Player.objects.filter(uuid=player_uuid, secret_key=player_secret_key)
            if check_player:
                player = check_player.first()
                total_played_matches = 0
                win_match = 0
                matches = []
                team_ids = list(player.team.values_list('id', flat=True))

                today = timezone.now().date()
                twelve_months_ago = today - timedelta(days=365)
                if len(team_ids) > 0:
                    for team_id in team_ids:
                        check_match = Tournament.objects.filter(
                            Q(team1_id=team_id, is_completed=True) | Q(team2_id=team_id, is_completed=True))
                        win_check_match = check_match.filter(winner_team_id=team_id).count()
                        total_played_matches += check_match.count()
                        win_match += win_check_match
                        match = Tournament.objects.filter(
                                    Q(team1=team_id) | Q(team2=team_id),
                                    is_completed=True,
                                    playing_date_time__date__gte=twelve_months_ago,
                                    playing_date_time__date__lte=today
                                ).annotate(
                                    month=TruncMonth('playing_date_time')
                                ).values(
                                    'month'
                                ).annotate(
                                    matches_played=Count('id'),
                                    wins=Count(Case(
                                        When(winner_team=team_id, then=1),
                                        output_field=IntegerField()
                                    )),
                                ).order_by('month')
                        matches.extend(match)
                lost_match = total_played_matches - win_match

                match_count = {"total_matches": total_played_matches,
                            "wim_matches": win_match,
                            "lost_matches": lost_match
                            }

                months = []
                for i in range(12):
                    month = today - relativedelta(months=i)
                    first_day_of_month = month.replace(day=1)
                    months.append(first_day_of_month.strftime('%Y-%m'))
                months = sorted(list(set(months)))
                match_data = {month: {'matches_played': 0, 'wins': 0} for month in months}

                for mat in matches:
                    month_str = mat['month'].strftime('%Y-%m')
                    match_data[month_str]['matches_played'] += mat['matches_played']
                    match_data[month_str]['wins'] += mat['wins']

                sorted_months = sorted(months) 
                matches_played = [match_data[month]['matches_played'] for month in sorted_months]
                wins = [match_data[month]['wins'] for month in sorted_months]

                data_set = {"month": sorted_months,
                            "match_played": matches_played,
                            "win": wins
                            }
                data['status'] = status.HTTP_200_OK
                data['match_count'] = match_count
                data['data_set'] = data_set
                data['message'] = 'Data fetched successfully.'
            else:
                data['status'] = status.HTTP_200_OK
                data['match_count'] = []
                data['data_set'] = []
                data['message'] = 'User is not a player.'
        else:
            data['status'] = status.HTTP_200_OK
            data['match_count'] = []
            data['data_set'] = []
            data['message'] = 'User not found.'
    except Exception as e:
        data['status'] = status.HTTP_400_BAD_REQUEST
        data['match_count'] = []
        data['data_set'] = []
        data['message'] = f'{str(e)}'
    return Response(data)



"""
player edit api
only who create this player he/she can edit this player
"""
@api_view(('POST',))
def edit_player(request):
    data = {'status':'','message':''}
    try:        
        user_uuid = request.data.get('user_uuid')
        user_secret_key = request.data.get('user_secret_key')
        p_uuid = request.data.get('p_uuid')
        p_secret_key = request.data.get('p_secret_key')
        p_first_name = request.data.get('p_first_name')
        p_last_name = request.data.get('p_last_name')
        p_phone_number = request.data.get('p_phone_number')
        p_ranking = request.data.get('p_ranking')
        p_image = request.FILES.get('p_image')
        p_gender = request.data.get('p_gender')

        check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
        if check_user.exists() :
            get_user = check_user.first()
            check_player = Player.objects.filter(uuid=p_uuid,secret_key=p_secret_key,created_by=get_user)
            if check_player.exists():
                player_full_name = f"{p_first_name} {p_last_name}"
                identify_player = f"{str(p_first_name)[0]} {str(p_last_name)[0]}"
                if p_image is not None:
                    check_player.update(
                                    player_first_name=p_first_name,
                                    player_last_name=p_last_name,
                                    player_full_name=player_full_name,
                                    player_phone_number=p_phone_number,
                                    player_ranking=p_ranking,
                                    identify_player=identify_player,
                                    player_image=p_image
                                )
                else:
                    check_player.update(
                                    player_first_name=p_first_name,
                                    player_last_name=p_last_name,
                                    player_full_name=player_full_name,
                                    player_phone_number=p_phone_number,
                                    player_ranking=p_ranking,
                                    identify_player=identify_player,
                                )
                if cache.has_key("player_list"):
                    cache.delete("player_list")
                p_user = User.objects.filter(id=check_player.first().player.id)
                if p_user.exists() :
                    get_p_user = p_user.first()
                    get_p_user.first_name = p_first_name
                    get_p_user.last_name = p_last_name
                    get_p_user.rank = p_ranking
                    get_p_user.gender = p_gender
                    get_p_user.phone = p_phone_number
                    if p_image is not None:
                        get_p_user.image = p_image
                    get_p_user.save()
                data["status"], data["message"] = status.HTTP_200_OK, "player Updated successfully"
            else:
                data["status"], data["message"] = status.HTTP_200_OK, "player not found"
        else:
            data["status"], data["message"] = status.HTTP_200_OK, "user not found"
    except Exception as e :
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
    return Response(data)

"""
player delete api
only who create this player he/she can delete this player
"""
@api_view(('POST',))
def delete_player(request):
    data = {'status':'','message':''}
    try:        
        user_uuid = request.data.get('user_uuid')
        user_secret_key = request.data.get('user_secret_key')
        p_email = request.data.get('p_email')
        p_uuid = request.data.get('p_uuid')
        p_secret_key = request.data.get('p_secret_key')
        
        check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
        if check_user.exists():
            get_player = User.objects.filter(email=p_email)
            check_player = Player.objects.filter(uuid=p_uuid,secret_key=p_secret_key)
            if get_player.exists() and check_player.exists():
                if check_user.first().is_admin:
                    get_player.delete()
                    check_player.delete()                    
                elif check_player.first().created_by == check_user.first():
                    get_player.delete()
                    check_player.delete()
                else:
                    pass
                if cache.has_key("player_list"):
                    cache.delete("player_list")
                data["status"], data["message"] = status.HTTP_200_OK, "player Deleted successfully"
            
            else:
                data["status"], data["message"] = status.HTTP_200_OK, "player not found"
        else:
            data["status"], data["message"] = status.HTTP_200_OK, "user not found"
    except Exception as e :
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
    return Response(data)



from datetime import timedelta
from dateutil.relativedelta import relativedelta
from math import radians, cos, sin, asin, sqrt
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
from apps.team.helper import *
from django.db.models import Avg, Count, Value, F, Q, Case, When, IntegerField, FloatField
from django.db.models.functions import Cast


"""
team list api
all user can show the team list
team list search by keyword
filter team list
"""
@api_view(('GET',))
def team_list_using_pagination(request):
    data = {
        'status': '',
        'count': '',
        'previous': '',
        'next': '',
        'data': [],
        'message': ''
    }
    try:    
        user_uuid = request.GET.get('user_uuid')
        user_secret_key = request.GET.get('user_secret_key')
        search_text = request.GET.get('search_text')
        ordering = request.GET.get('ordering')
        team_person = request.GET.get('team_person')
        team_type = request.GET.get('team_type')
        start_rank = request.GET.get('start_rank')
        end_rank = request.GET.get('end_rank')
        
        check_user = User.objects.filter(uuid=user_uuid, secret_key=user_secret_key)
        if check_user.exists():
            user = check_user.first()
            if user.is_admin or user.is_organizer:
                teams_query = Team.objects.annotate(
                    team_rank=Avg(
                        Case(
                            When(
                                player__player__rank__isnull=False,
                                then=Cast(F("player__player__rank"), output_field=FloatField()),
                            ),
                            default=Value(1.0, output_field=FloatField()),
                            output_field=FloatField(),
                        )
                    )
                )
            else:
                teams_query = Team.objects.filter(created_by=user).annotate(
                    team_rank=Avg(
                        Case(
                            When(
                                player__player__rank__isnull=False,
                                then=Cast(F("player__player__rank"), output_field=FloatField()),
                            ),
                            default=Value(1.0, output_field=FloatField()),
                            output_field=FloatField(),
                        )
                    )
                )

            if search_text:
                teams_query = teams_query.filter(name__icontains=search_text)

            if ordering == "latest":
                teams_query = teams_query.order_by('-id')
            elif ordering == "a-z":
                teams_query = teams_query.order_by('name')
            else:
                teams_query = teams_query.order_by('-id')

            if team_person not in [None, "null", "", "None"]:
                teams_query = teams_query.filter(team_person__icontains=team_person)

            if team_type not in [None, "null", "", "None"]:
                teams_query = teams_query.filter(team_type__iexact=team_type)

            if start_rank not in [None, "null", "", "None"] and end_rank not in [None, "null", "", "None"]:
                teams_query = teams_query.filter(
                Q(team_rank__gte=start_rank) &
                Q(team_rank__lte=end_rank)
            )
            paginator = PageNumberPagination()
            paginator.page_size = 10
            paginated_teams = paginator.paginate_queryset(teams_query, request)

            main_data = []
            for team in paginated_teams:
                players = Player.objects.filter(team=team)
                team_rank = sum(float(player.player.rank) if player.player.rank not in ["", "null", None] else 1 for player in players) / max(len(players), 1)
                
                team_data = TeamListSerializer(team).data
                team_data['team_uuid'] = team_data.pop('uuid')
                team_data['team_secret_key'] = team_data.pop('secret_key')
                team_data['team_name'] = team_data.pop('name')
                team_data['location'] = team_data.pop('location')
                team_data['team_rank'] = team_rank
                team_data['is_edit'] = team.created_by_id == user.id
                main_data.append(team_data)

            paginated_response = paginator.get_paginated_response(main_data)
            
            data["status"] = status.HTTP_200_OK
            data["count"] = paginated_response.data["count"]
            data["previous"] = paginated_response.data["previous"]
            data["next"] = paginated_response.data["next"]
            data["data"] = paginated_response.data["results"]
            data["message"] = "Data found for Admin" if user.is_admin or user.is_organizer else "Data found"
            
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
creat team
any user can creat his/her own team
 .can select one or two member team
 .can create men/women/co-ed team
"""
@api_view(('POST',))
def create_team(request):
    data = {'status': '', 'message': ''}
    try:        
        user_uuid = request.data.get('user_uuid')
        user_secret_key = request.data.get('user_secret_key')

        team_name = request.data.get('team_name')
        team_location = request.data.get('team_location')
        team_image = request.data.get('team_image')
        team_person = request.data.get('team_person')
        team_type = request.data.get('team_type')

        p1_uuid = request.data.get('p1_uuid')
        p1_secret_key = request.data.get('p1_secret_key')

        p2_uuid = request.data.get('p2_uuid')
        p2_secret_key = request.data.get('p2_secret_key')

        check_user = User.objects.filter(uuid=user_uuid, secret_key=user_secret_key)

        if not check_user.exists():
            data["status"], data["message"] = status.HTTP_404_NOT_FOUND, "User not found"
            return Response(data)

        if not team_name or not team_person:
            data["status"], data["message"] = status.HTTP_403_FORBIDDEN, "Team Name and Team Type (2 person or 4 person) required"
            return Response(data)

        if team_person == "Two Person Team":
            if not p1_uuid or not p1_secret_key or not p2_uuid or not p2_secret_key:
                data["status"], data["message"] = status.HTTP_400_BAD_REQUEST, "Players details required for Two Person Team"
                return Response(data)
            if not Player.objects.filter(uuid=p1_uuid, secret_key=p1_secret_key).exists() or not Player.objects.filter(uuid=p2_uuid, secret_key=p2_secret_key).exists():
                data["status"], data["message"] = status.HTTP_400_BAD_REQUEST, "One or both players do not exist"
                return Response(data)
        elif team_person == "One Person Team":
            if not p1_uuid or not p1_secret_key:
                data["status"], data["message"] = status.HTTP_400_BAD_REQUEST, "Player details required for One Person Team"
                return Response(data)
            if not Player.objects.filter(uuid=p1_uuid, secret_key=p1_secret_key).exists():
                data["status"], data["message"] = status.HTTP_400_BAD_REQUEST, "Player does not exist"
                return Response(data)

        if team_person == "Two Person Team":
            obj = GenerateKey()
            team_secret_key = obj.gen_team_key()
            player1_secret_key = obj.gen_player_key()
            obj2 = GenerateKey()
            player2_secret_key = obj2.gen_player_key()
            created_by_id = check_user.first().id
            if team_image is not None:
                team_image = team_image
            else:
                team_image = None
            save_team = Team(secret_key=team_secret_key, name=team_name, location=team_location, team_person=team_person, team_type=team_type, team_image=team_image, created_by_id=created_by_id)
            save_team.save()
            if cache.has_key("team_list"):
                cache.delete("team_list")
            p1 = Player.objects.filter(uuid=p1_uuid, secret_key=p1_secret_key).first()
            p1.team.add(save_team.id)
            p2 = Player.objects.filter(uuid=p2_uuid, secret_key=p2_secret_key).first()
            p2.team.add(save_team.id)
            check_user.update(is_team_manager=True)
            ##
            # send notification
            #player 1
            player1 = p1.player
            player2 = p2.player
            titel="Team Created"
            notify_message1 = f"Hey {player1.first_name}! You have been added to an awesome team - {save_team.name}"
            notify_edited_player(player1.id, titel, notify_message1)
            
            #player 2
            notify_message2 = f"Hey {player2.first_name}! You have been added to an awesome team - {save_team.name}"
            notify_edited_player(player2.id, titel, notify_message2)
            data["status"], data["message"] = status.HTTP_200_OK, "Team and Player created successfully"
        
        elif team_person == "One Person Team":
            obj = GenerateKey()
            team_secret_key = obj.gen_team_key()
            created_by_id = check_user.first().id
            if team_image is not None:
                team_image = team_image
            else:
                team_image = None
            save_team = Team(secret_key=team_secret_key, name=team_name, location=team_location, team_person=team_person, team_type=team_type, team_image=team_image, created_by_id=created_by_id)
            save_team.save()
            if cache.has_key("team_list"):
                cache.delete("team_list")
            p1 = Player.objects.filter(uuid=p1_uuid, secret_key=p1_secret_key).first()
            p1.team.add(save_team.id)
            check_user.update(is_team_manager=True)
            ##
            # send notification
            #player 1
            
            player1 = p1.player
            titel="Team Created"
            notify_message = f"Hey {player1.first_name}! You have been added to an awesome team - {save_team.name}"
            notify_edited_player(player1.id, titel, notify_message)
            data["status"], data["message"] = status.HTTP_200_OK, "Team and Player created successfully"

    except Exception as e:
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, str(e)

    return Response(data)

"""
team view api
any user can show the team view
"""
@api_view(('GET',))
def team_view(request):
    data = {'status':'','message':''}
    try:        
        user_uuid = request.GET.get('user_uuid')
        user_secret_key = request.GET.get('user_secret_key')
        t_uuid = request.GET.get('t_uuid')
        t_secret_key = request.GET.get('t_secret_key')

        check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
        if check_user.exists() :
            check_team = Team.objects.filter(uuid=t_uuid,secret_key=t_secret_key)
            if check_team.exists() :
                main_data = check_team.values('id','uuid','secret_key','name','location','created_by__first_name','created_by__last_name',
                                            'team_image','created_by__uuid','created_by__secret_key','team_type','team_person')
                
                get_team = check_team.first()

                player_data = Player.objects.filter(team__id=get_team.id).values("id","uuid","secret_key","player__email",
                                                    "player__first_name","player__last_name","player__gender","player__image")

                data["status"], data["data"], data["message"] = status.HTTP_200_OK, {"team_data":main_data,"player_data":player_data},"Data found"
            else:
                data["status"], data["message"] = status.HTTP_404_NOT_FOUND, "Team not found"
        else:
            data["status"], data["message"] = status.HTTP_404_NOT_FOUND, "User not found"  
    except Exception as e :
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
    return Response(data)


"""
get the team list which team user created 
"""
@api_view(("GET",))
def my_team_list(request):
    data = {
        'status': '',
        'count': '',
        'previous': '',
        'next': '',
        'data': [],
        'message': ''
    }
    try:
        user_uuid = request.GET.get('user_uuid')
        user_secret_key = request.GET.get('user_secret_key')
        search_text = request.GET.get('search_text')
        ordering = request.GET.get('ordering')
        team_person = request.GET.get('team_person')
        team_type = request.GET.get('team_type')
        start_rank = request.GET.get('start_rank')
        end_rank = request.GET.get('end_rank')

        check_user = User.objects.filter(uuid=user_uuid, secret_key=user_secret_key).first()
        if check_user:
            
            teams_query = Team.objects.filter(
                Q(created_by=check_user) | Q(player__player=check_user)
            ).distinct()

            if search_text:
                teams_query = teams_query.filter(name__icontains=search_text)

            ordering_map = {
                "latest": '-id',
                "a-z": 'name'
            }
            teams_query = teams_query.order_by(ordering_map.get(ordering, '-id'))

            # Prefetch related data
            teams_query = teams_query.prefetch_related('player_set')
            
            if team_person not in [None, "null", "", "None"]:
                teams_query = teams_query.filter(team_person__icontains=team_person)

            if team_type not in [None, "null", "", "None"]:
                teams_query = teams_query.filter(team_type__iexact=team_type)

            # Add annotations for rank
            teams_query = teams_query.annotate(
                team_rank=Avg(
                        Case(
                            When(
                                player__player__rank__isnull=False,
                                then=Cast(F("player__player__rank"), output_field=FloatField()),
                            ),
                            default=Value(1.0, output_field=FloatField()),
                            output_field=FloatField(),
                        )
                    )
                )
            if start_rank not in [None, "null", "", "None"] and end_rank not in [None, "null", "", "None"]:
                teams_query = teams_query.filter(
                Q(team_rank__gte=start_rank) &
                Q(team_rank__lte=end_rank)
            )

            paginator = PageNumberPagination()
            paginator.page_size = 10
            paginated_teams = paginator.paginate_queryset(teams_query, request)

            main_data = []
            for team in paginated_teams:               
                team_data = TeamListSerializer(team).data
                team_data['team_uuid'] = team_data.pop('uuid')
                team_data['team_secret_key'] = team_data.pop('secret_key')
                team_data['team_name'] = team_data.pop('name')
                team_data['location'] = team_data.pop('location')                
                team_data['is_edit'] = team.created_by_id == check_user.id
                main_data.append(team_data)

            paginated_response = paginator.get_paginated_response(main_data)

            data["status"] = status.HTTP_200_OK
            data["count"] = paginated_response.data["count"]
            data["previous"] = paginated_response.data["previous"]
            data["next"] = paginated_response.data["next"]
            data["data"] = paginated_response.data["results"]
            data["message"] = "Data found for Admin" if check_user.is_admin or check_user.is_organizer else "Data found"

        else:
            data["status"] = status.HTTP_401_UNAUTHORIZED
            data["message"] = "Unauthorized access"

    except Exception as e:
        data["status"] = status.HTTP_200_OK
        data["message"] = str(e)

    return Response(data)

"""
get the team profile details
sub section of team view api
"""
@api_view(("GET",))
def team_profile_details(request):
    data = {'status':'','message':''}
    try:        
        user_uuid = request.GET.get('user_uuid')
        user_secret_key = request.GET.get('user_secret_key')
        t_uuid = request.GET.get('t_uuid')
        t_secret_key = request.GET.get('t_secret_key')
        check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
        if check_user.exists() :
            user = check_user.first()
            check_team = Team.objects.filter(uuid=t_uuid,secret_key=t_secret_key)
            if check_team.exists() :
                team = check_team.first()
                serializer  = TeamListSerializer(team)
                team_data = serializer.data
                team_data['is_edit'] = team_data['created_by_uuid'] == str(user.uuid)
                data['status'] = status.HTTP_200_OK
                data['team_data'] = team_data
                data['message'] = f'Team details fetched successfully.'
            else:
                data['status'] = status.HTTP_404_NOT_FOUND
                data['team_data'] = []
                data['message'] = f'Team not found.' 
        else:
            data['status'] = status.HTTP_404_NOT_FOUND
            data['team_data'] = []
            data['message'] = f'User not found.'

    except Exception as e:
        data['status'] = status.HTTP_400_BAD_REQUEST
        data['team_data'] = []
        data['message'] = f'{str(e)}'
    return Response(data)

"""
get the team stats
sub section of team view api
"""
@api_view(("GET",))
def team_statistics(request):
    data = {'status':'','message':''}
    try:        
        user_uuid = request.GET.get('user_uuid')
        user_secret_key = request.GET.get('user_secret_key')
        t_uuid = request.GET.get('t_uuid')
        t_secret_key = request.GET.get('t_secret_key')
        check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
        if check_user.exists() :
            check_team = Team.objects.filter(uuid=t_uuid,secret_key=t_secret_key)
            if check_team.exists() :
                team = check_team.first()
                today = timezone.now().date()
                twelve_months_ago = today - timedelta(days=365)
                check_match = Tournament.objects.filter(
                            Q(team1_id=team.id, is_completed=True) | Q(team2_id=team.id, is_completed=True))
                win_check_match = check_match.filter(winner_team_id=team.id).count()
                total_played_matches = check_match.count()
                win_match = win_check_match
                matches = Tournament.objects.filter(
                            Q(team1=team.id) | Q(team2=team.id),
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
                                When(winner_team=team.id, then=1),
                                output_field=IntegerField()
                            )),
                        ).order_by('month')
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
                data['message'] = 'Data fetched successfully.'
        else:
            data['status'] = status.HTTP_200_OK
            data['match_count'] = []
            data['data_set'] = []
            data['message'] = 'Data fetched successfully.'

    except Exception as e:
        data['status'] = status.HTTP_400_BAD_REQUEST
        data['team_data'] = []
        data['message'] = f'{str(e)}'
    return Response(data)

"""
get the team match history
sub section of team view api
"""
@api_view(("GET",))
def team_match_history(request):
    data = {'status':'', 'message':''}
    try:        
        user_uuid = request.GET.get('user_uuid')
        user_secret_key = request.GET.get('user_secret_key')
        t_uuid = request.GET.get('t_uuid')
        t_secret_key = request.GET.get('t_secret_key')
        check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
        matches = []
        if check_user.exists() :
            check_team = Team.objects.filter(uuid=t_uuid,secret_key=t_secret_key)
            if check_team.exists() :
                team = check_team.first()
                match = Tournament.objects.filter(Q(team1_id=team.id) | Q(team2_id=team.id)).filter(is_completed=True).order_by("playing_date_time")
                if match:
                    serializer = TournamentSerializer(match, many=True)
                    matches.append(serializer.data)
                for match in matches:
                    for mat in match:                    
                        mat["team1"]["player_images"] = [
                                player_image if player_image else None 
                                for player_image in Player.objects.filter(team__id=mat["team1"]["id"]).values_list("player__image", flat=True)
                            ]
                        mat["team2"]["player_images"] = [
                                player_image if player_image else None 
                                for player_image in Player.objects.filter(team__id=mat["team2"]["id"]).values_list("player__image", flat=True)
                            ]
                        mat["team1"]["player_names"] = [
                                player_name for player_name in Player.objects.filter(team__id=mat["team1"]["id"]).values_list("player_full_name", flat=True)
                            ]
                        mat["team2"]["player_names"] = [
                                player_name for player_name in Player.objects.filter(team__id=mat["team2"]["id"]).values_list("player_full_name", flat=True)
                            ]    
                data['status'] = status.HTTP_200_OK
                data['message'] = f"Data fetched successfully."  
                data['data'] = matches    
            else:
                data['status'] = status.HTTP_404_NOT_FOUND
                data['message'] = f"Team not found."  
                data['data'] = []                      
        else:
            data['status'] = status.HTTP_404_NOT_FOUND
            data['message'] = f"User not found."  
            data['data'] = []
    except Exception as e:
        data['status'] = status.HTTP_400_BAD_REQUEST
        data['message'] = f"{e}"
        data['data'] = []
    return Response(data)    



"""
team edit view
user can edit, who create the team
"""
@api_view(('POST',))
def edit_team(request):
    data = {'status':'', 'message':''}
    try:        
        user_uuid = request.data.get('user_uuid')
        user_secret_key = request.data.get('user_secret_key')

        t_uuid = request.data.get('t_uuid')
        t_secret_key = request.data.get('t_secret_key')

        team_name = request.data.get('team_name')
        team_location = request.data.get('team_location')
        team_image = request.data.get('team_image')
        team_person = request.data.get('team_person')
        team_type = request.data.get('team_type')

        p1_uuid = request.data.get('p1_uuid')
        p1_secret_key = request.data.get('p1_secret_key')

        p2_uuid = request.data.get('p2_uuid')
        p2_secret_key = request.data.get('p2_secret_key')

        removed_players = []
        new_players = []

        check_user = User.objects.filter(uuid=user_uuid, secret_key=user_secret_key)
        if check_user.exists(): 
            if not team_name or not team_person:
                data["status"], data["message"] = status.HTTP_403_FORBIDDEN, "Team Name and Team Type (2 person or 4 person) required"
                return Response(data)

            if team_person == "Two Person Team":
                if not p1_uuid or not p1_secret_key or not p2_uuid or not p2_secret_key:
                    data["status"], data["message"] = status.HTTP_403_FORBIDDEN, "Player1 and Player2's email and phone number required"
                    return Response(data)
                else:
                    check_team = Team.objects.filter(uuid=t_uuid, secret_key=t_secret_key)
                    check_player1 = Player.objects.filter(uuid=p1_uuid, secret_key=p1_secret_key)
                    check_player2 = Player.objects.filter(uuid=p2_uuid, secret_key=p2_secret_key)
                    
                    if check_team.exists():
                        team_instance = check_team.first()
                        team_instance.name = team_name
                        team_instance.location = team_location
                        team_instance.team_person = team_person
                        team_instance.team_type = team_type
                        
                        if team_image is not None:
                            team_instance.team_image = team_image
                            
                        pre_player_list = Player.objects.filter(team__id=team_instance.id)
                        for pre_player in pre_player_list:
                            removed_players.append(pre_player.id)
                            pre_player.team.remove(team_instance.id)

                        check_player1_instance = check_player1.first()
                        check_player1_instance.team.add(team_instance.id)
                        new_players.append(check_player1_instance.id)
                        
                        check_player2_instance = check_player2.first()
                        check_player2_instance.team.add(team_instance.id)
                        new_players.append(check_player2_instance.id)
                        team_instance.save()
                        if cache.has_key("team_list"):
                            cache.delete("team_list")
                        #add notification
                        add, rem = check_add_player(new_players, removed_players)
                        
                        titel = "Team Membership Modification"
                        # notification for added player
                        for r in rem:
                            message = f"You have been removed from team {team_instance.name}"
                            user_id = Player.objects.filter(id=r).first().player.id
                            notify_edited_player(user_id, titel, message)
                        
                        titel = "Team Membership Modification"
                        for r in add:
                            message = f"You have been added to team {team_instance.name}"
                            user_id = Player.objects.filter(id=r).first().player.id
                            notify_edited_player(user_id, titel, message)
                        data["status"], data["message"] = status.HTTP_200_OK, f"Team edited successfully"
                    else:
                        data["status"], data["message"] = status.HTTP_404_NOT_FOUND, "Team not found"
                    return Response(data)
                    
                
            if team_person == "One Person Team":
                if not p1_uuid or not p1_secret_key:
                    data["status"], data["message"] = status.HTTP_403_FORBIDDEN, "Player's email and phone number required"
                    return Response(data)
                else:
                    check_team = Team.objects.filter(uuid=t_uuid, secret_key=t_secret_key)
                    check_player = Player.objects.filter(uuid=p1_uuid, secret_key=p1_secret_key)
                    
                    if check_team.exists() and check_player.exists():
                        team_instance = check_team.first()
                        team_instance.name = team_name
                        team_instance.location = team_location
                        team_instance.team_person = team_person
                        team_instance.team_type = team_type
                        
                        if team_image is not None:
                            team_instance.team_image = team_image
                        
                        team_instance.save() 
                        if cache.has_key("team_list"):
                            cache.delete("team_list")                       
                        remove_player_team = Player.objects.filter(team__id=team_instance.id)
                        for remove_player in remove_player_team:
                            removed_players.append(remove_player.id)
                            remove_player.team.remove(team_instance.id)

                        check_player_instance = check_player.first()
                        check_player_instance.team.add(team_instance.id)
                        new_players.append(check_player_instance.id)
                        # notification
                        add, rem = check_add_player(new_players, removed_players)
                        
                        titel = "Team Membership Modification"
                        # notification for added player
                        for r in rem:
                            message = f"You have been removed from team {team_instance.name}"
                            user_id = Player.objects.filter(id=r).first().player.id
                            notify_edited_player(user_id, titel, message)
                        
                        for r in add:
                            message = f"You have been added to team {team_instance.name}"
                            user_id = Player.objects.filter(id=r).first().player.id
                            notify_edited_player(user_id, titel, message)
                        data["status"], data["message"] = status.HTTP_200_OK, f"Team edited successfully"
                    else:
                        data["status"], data["message"] = status.HTTP_404_NOT_FOUND, "Team not found"
                    
                    add, rem = check_add_player(new_players, removed_players)
                    print(add, rem)
                    return Response(data)
            else:
                data["status"], data["message"] = status.HTTP_404_NOT_FOUND, "Something is wrong"
        else:
            data["status"], data["message"] = status.HTTP_404_NOT_FOUND, "User not found"
    except Exception as e:
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
    
    print(removed_players)  
    print(new_players)  
    
    return Response(data)

"""
team delete view
user can delete, who create the team
"""
@api_view(('POST',))
def delete_team(request):
    data = {'status':'','message':''}
    try:        
        user_uuid = request.data.get('user_uuid')
        user_secret_key = request.data.get('user_secret_key')

        team_uuid = request.data.get('team_uuid')
        team_secret_key = request.data.get('team_secret_key')

        team_league  = Team.objects.filter(uuid=team_uuid,secret_key=team_secret_key)
        check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
        if check_user.exists():
            team_league  = Team.objects.filter(uuid=team_uuid,secret_key=team_secret_key, created_by=check_user.first())
            if team_league.exists():
                team_id = team_league.first().id 
                check_team_have_any_tournament = Leagues.objects.filter(registered_team__in=[team_id], is_complete=False)
                if not check_team_have_any_tournament.exists():
                    team_name = team_league.first().name
                    players = Player.objects.filter(team__id=team_id)
                    players_list = list(players)

                    team_league.first().delete()
                    if cache.has_key("team_list"):
                        cache.delete("team_list")
                    titel = "Team Membership Modification"
                    message = f"Hey player! the team {team_name} has been deleted."
                    for player in players_list:
                        notify_edited_player(player.player.id, titel, message)

                    data["status"], data["message"] = status.HTTP_200_OK, "Team Deleted"
                else:
                    data["status"], data["message"] = status.HTTP_200_OK, "Unable to delete team. This team cannot be deleted as it is currently participating in a tournament."
            else:
                data["status"], data["message"] = status.HTTP_404_NOT_FOUND, "Team not found"
        else:
            data["status"], data["message"] = status.HTTP_404_NOT_FOUND, "User not found"
    except Exception as e :
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
    return Response(data)


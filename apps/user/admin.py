from django.contrib import admin
from apps.user.models import *
# Register your models here.

admin.site.register(User)
admin.site.register(Role)
admin.site.register(IsSponsorDetails)
admin.site.register(AppUpdate)
admin.site.register(BasicQuestionsUser)
admin.site.register(UserAnswer)
admin.site.register(MatchingPlayers)
admin.site.register(FCMTokenStore)
class LogEntryAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'model_name', 'instance_id', 'timestamp')
    ordering = ('-timestamp',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs
    
    list_per_page = 20

admin.site.register(LogEntry, LogEntryAdmin)

admin.site.register(AppVersionUpdate)

admin.site.register(Subscription)
admin.site.register(SubscriptionPlan)
admin.site.register(AllPaymentsTable)
admin.site.register(Features)
admin.site.register(Wallet)
@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'sender', 'reciver', 'transaction_type', 'transaction_for', 'amount', 'created_at')
    list_filter = ('transaction_type', 'transaction_for', 'created_at')
    search_fields = ('transaction_id', 'sender__username', 'reciver__username')
    ordering = ('-created_at',)
    readonly_fields = ('transaction_id',)
    fields = ('transaction_id', 'sender', 'reciver', 'transaction_type', 'transaction_for', 
              'reciver_cost', 'admin_cost', 'getway_charge', 'amount', 'payment_id', 
              'json_response', 'description', 'created_at') 
    
admin.site.register(AdminWallet)
admin.site.register(AdminWalletTransaction)
admin.site.register(WithdrawalRequest)
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import Test, Question, Answer, UserAction, UserActivityFeature, PredictionResult

# 自定义管理后台
admin.site.site_url = '/dashboard/'  # 修改"查看站点"链接指向管理面板

# 注册模型
class QuestionInline(admin.StackedInline):  # 改用StackedInline更清晰
    model = Question
    fields = ('text', 'option_a', 'option_b', 'option_c', 'option_d', 'correct_answer')
    extra = 1  # 默认只显示一个空表单，降低复杂度
    min_num = 0  # 不强制要求添加问题
    can_delete = True

@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_at')
    search_fields = ('title', 'description')
    inlines = [QuestionInline]
    
    def save_model(self, request, obj, form, change):
        """先保存试卷"""
        super().save_model(request, obj, form, change)
    
    def save_formset(self, request, form, formset, change):
        """自定义保存内联表单集的方法"""
        if form.is_valid():
            # 先获取或创建试卷实例
            test_instance = form.instance
            
            # 确保试卷已保存并有ID
            if not test_instance.id:
                test_instance.save()
            
            # 保存问题前检查数据
            instances = formset.save(commit=False)
            for instance in instances:
                # 设置关联
                instance.paper = test_instance
                
                # 只有在试卷已保存后才生成test_id
                if test_instance.id and not instance.test_id:
                    instance.test_id = f"paper_{test_instance.id}"
                
                # 保存问题实例
                instance.save()
            
            # 处理已删除的实例
            for obj in formset.deleted_objects:
                obj.delete()
            
            # 保存多对多关系
            formset.save_m2m()

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('text', 'test_id', 'paper', 'correct_answer')
    list_filter = ('test_id', 'paper')
    search_fields = ('text', 'test_id')
    
    # 简化问题添加表单
    fieldsets = (
        ('基本信息', {
            'fields': ('text', 'paper',)
        }),
        ('选项', {
            'fields': ('option_a', 'option_b', 'option_c', 'option_d', 'correct_answer')
        }),
        ('高级选项', {
            'classes': ('collapse',),
            'fields': ('test_id',),
        }),
    )

@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ('question', 'user_answer', 'is_correct')
    list_filter = ('is_correct',)

@admin.register(UserAction)
class UserActionAdmin(admin.ModelAdmin):
    list_display = ('user', 'timestamp', 'action_type', 'test_id')
    list_filter = ('action_type', 'test_id', 'user')
    search_fields = ('user__username', 'test_id')

@admin.register(UserActivityFeature)
class UserActivityFeatureAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'test_id')
    list_filter = ('test_id',)
    search_fields = ('user_id', 'test_id')

@admin.register(PredictionResult)
class PredictionResultAdmin(admin.ModelAdmin):
    list_display = ('user', 'test_id', 'timestamp', 'prediction')
    list_filter = ('prediction', 'test_id')
    search_fields = ('user__username', 'test_id')

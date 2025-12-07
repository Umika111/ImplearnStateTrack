from django.urls import path
from . import views
from django.shortcuts import redirect

urlpatterns = [
    path('', lambda request: redirect('login'), name='home'),  # 添加根路径重定向到登录页面
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),  # 添加登出路由
    path('quiz/', views.quiz, name='quiz'),
    path('quiz/questions/', views.quiz_questions, name='quiz_questions'),
    path('result/', views.result, name='result'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('record_action/', views.record_action, name='record_action'),
    path('process_quiz_data/', views.process_quiz_data, name='process_quiz_data'),  # 添加处理表单提交的 URL 路径
    path('predict_behavior/', views.predict_student_behavior, name='predict_behavior'),
    path('student_records/', views.student_records, name='student_records'),
]
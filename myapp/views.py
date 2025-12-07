from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from .forms import TestSelectionForm, QuizForm, SignUpForm, CustomAuthenticationForm
from .models import Question, UserAction,Answer, Test, PredictionResult
from django.contrib.auth.decorators import login_required
from datetime import timedelta
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import UserAction, UserActivityFeature
from datetime import datetime
import pandas as pd
import json
import csv
import torch
import numpy as np
from django.contrib import messages

def quiz(request):
    if request.method == 'POST':
        test_selection_form = TestSelectionForm(request.POST)
        if test_selection_form.is_valid():
            selected_test_id = test_selection_form.cleaned_data['test_id']
            request.session['selected_test_id'] = selected_test_id
            return redirect('quiz_questions')  # 确保这里使用正确的 URL 名称
    else:
        test_selection_form = TestSelectionForm()

    return render(request, 'quiz.html', {'test_selection_form': test_selection_form})


@login_required
def quiz_questions(request):
    selected_test_id = request.session.get('selected_test_id')
    if not selected_test_id:
        return redirect('quiz')  # 如果没有选择试卷，重定向到选择试卷页面

    # 获取问题列表
    if selected_test_id.startswith('paper_'):
        # 新版本: 从Test模型中获取问题
        paper_id = selected_test_id.replace('paper_', '')
        try:
            paper = Test.objects.get(id=paper_id)
            questions = Question.objects.filter(paper=paper)
        except Test.DoesNotExist:
            questions = Question.objects.filter(test_id=selected_test_id)
    else:
        # 旧版本: 直接使用test_id过滤
        questions = Question.objects.filter(test_id=selected_test_id)

    if not questions.exists():
        messages.error(request, "该试卷没有问题，请选择其他试卷。")
        return redirect('quiz')

    if request.method == 'POST':
        form = QuizForm(request.POST, questions=questions)
        if form.is_valid():
            score = 0
            total_questions = questions.count()
            correct_count = 0
            
            for question in questions:
                user_answer = form.cleaned_data.get(f'question_{question.id}')
                if user_answer:
                    is_correct = user_answer == question.correct_answer
                    if is_correct:
                        correct_count += 1
                    Answer.objects.create(
                        question=question, 
                        user_answer=user_answer, 
                        is_correct=is_correct
                    )
                
                    # 保存用户行为数据
                    UserAction.objects.create(
                        user=request.user,
                        action_type='respond',
                        test_id=selected_test_id,
                        item_id=str(question.id),
                        cursor_time=None,
                        source='diagnosis',
                        user_answer=user_answer
                    )
            
            # 计算得分
            if total_questions > 0:
                score = (correct_count / total_questions) * 100
            
            # 创建学习记录
            try:
                # 尝试简单的预测（示例：如果分数低于60%，则需要提醒）
                prediction = 1 if score < 60 else 0
                
                # 创建预测结果记录
                PredictionResult.objects.create(
                    user=request.user,
                    test_id=selected_test_id,
                    prediction=prediction
                )
            except Exception as e:
                print(f"创建学习记录失败: {str(e)}")  # 记录错误但不中断流程
            
            request.session['score'] = score
            request.session['correct_count'] = correct_count
            request.session['total_questions'] = total_questions
            return redirect('result')
    else:
        form = QuizForm(questions=questions)

    # 保存用户进入试卷的行为数据
    UserAction.objects.create(
        user=request.user,
        action_type='enter',
        test_id=selected_test_id,
        cursor_time=timedelta(seconds=0),
        source='diagnosis',
        user_answer=None
    )

    # 获取试卷标题
    try:
        if selected_test_id.startswith('paper_'):
            paper_id = selected_test_id.replace('paper_', '')
            paper = Test.objects.get(id=paper_id)
            test_title = paper.title
        else:
            test_title = f"试卷-{selected_test_id}"
    except:
        test_title = selected_test_id

    return render(request, 'quiz_questions.html', {
        'form': form,
        'test_title': test_title
    })

def result(request):
    score = request.session.get('score', 0)
    correct_count = request.session.get('correct_count', 0)
    total_questions = request.session.get('total_questions', 0)
    selected_test_id = request.session.get('selected_test_id', '')
    
    # 获取注意力状态
    attention_status = None
    if request.user.is_authenticated and selected_test_id:
        try:
            prediction_result = PredictionResult.objects.filter(
                user=request.user,
                test_id=selected_test_id
            ).order_by('-timestamp').first()
            
            if prediction_result:
                attention_status = "需要注意" if prediction_result.prediction == 1 else "状态良好"
        except Exception as e:
            print(f"获取注意力状态失败: {str(e)}")
    
    return render(request, 'result.html', {
        'score': score,
        'correct_count': correct_count,
        'total_questions': total_questions,
        'attention_status': attention_status
    })


def register(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # 自动登录新注册的用户
            return redirect('quiz')  # 重定向到首页或其他页面
    else:
        form = SignUpForm()
    return render(request, 'register.html', {'form': form})


def user_login(request):
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                if user.is_staff:  # 判断是否是管理员
                    return redirect('dashboard')  # 重定向到管理员后台页面
                else:
                    return redirect('quiz')  # 重定向到普通用户页面
    else:
        form = CustomAuthenticationForm()
    return render(request, 'login.html', {'form': form})




@require_POST
def record_action(request):
    data = json.loads(request.body)
    
    # 创建UserAction记录，处理item_id字段
    action_data = {
        'user': request.user,
        'action_type': data['action_type'],
        'test_id': data['test_id'],
        'cursor_time': None,  # 可以在这里计算时间差
        'source': data['source'],
        'user_answer': data['user_answer']
    }
    
    # 只有当item_id存在且不为None时才添加到数据中
    if 'item_id' in data and data['item_id'] is not None:
        action_data['item_id'] = data['item_id']
    
    UserAction.objects.create(**action_data)
    
    return JsonResponse({'status': 'success'})

@login_required
def dashboard(request):
    if not request.user.is_staff:
        return redirect('login')  # 如果不是管理员，重定向到登录页面
    
    # 获取统计数据
    test_count = Test.objects.count()
    question_count = Question.objects.count()
    user_count = User.objects.filter(is_staff=False).count()
    prediction_count = PredictionResult.objects.count()
    
    context = {
        'test_count': test_count,
        'question_count': question_count,
        'user_count': user_count,
        'prediction_count': prediction_count
    }
    
    return render(request, 'dashboard.html', context)

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import UserAction
import pandas as pd
from datetime import datetime

@require_POST
def process_quiz_data(request):
    selected_test_id = request.POST.get('selected_test_id')
    user_id = request.user.id
    activities = UserAction.objects.filter(user_id=user_id, test_id=selected_test_id)

    # 将查询结果转换为 DataFrame
    field_names = [field.name for field in UserAction._meta.get_fields()]

    df = pd.DataFrame(list(activities.values()), columns=field_names)

    # 编码 action_type, source 和 user_answer
    df['action_type_encoded'] = df['action_type'].astype('category').cat.codes
    df['source_encoded'] = df['source'].astype('category').cat.codes
    df['user_answer_encoded'] = df['user_answer'].astype('category').cat.codes

    # 提取时间戳，并计算时间差
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['hour'] = df['timestamp'].dt.hour
    df['minute'] = df['timestamp'].dt.minute
    df['day_of_week'] = df['timestamp'].dt.dayofweek
    df['time_diff'] = df['timestamp'].diff().dt.total_seconds()

    # 计算用户行为长度
    df['user_behavior_length'] = len(activities)

    # 序列化数据
    features = []
    for index, row in df.iterrows():
        feature = [
            row['cursor_time'] if pd.notnull(row['cursor_time']) else None,
            row['hour'],
            row['minute'],
            row['day_of_week'],
            row['action_type_encoded'],
            row['time_diff'] if pd.notnull(row['time_diff']) else None,
            row['user_behavior_length'],
            row['source_encoded'],
            row['user_answer_encoded']
        ]
        features.append(feature)

    # 输出到终端
    for feature in features:
        print(feature)

    return JsonResponse({'status': 'success'})

@require_POST
def predict_student_behavior(request):
    data = json.loads(request.body)
    user_id = request.user.id
    test_id = data.get('test_id')
    
    # 获取用户在该试卷的所有活动
    activities = UserAction.objects.filter(user_id=user_id, test_id=test_id)
    
    # 如果活动记录太少，不进行预测
    if activities.count() < 2:
        return JsonResponse({'status': 'not_enough_data'})
    
    # 将查询结果转换为 DataFrame
    field_names = [field.name for field in UserAction._meta.get_fields()]
    df = pd.DataFrame(list(activities.values()), columns=field_names)
    
    # 编码 action_type, source 和 user_answer
    df['action_type_encoded'] = df['action_type'].astype('category').cat.codes
    df['source_encoded'] = df['source'].astype('category').cat.codes
    df['user_answer_encoded'] = df['user_answer'].astype('category').cat.codes
    
    # 提取时间戳，并计算时间差
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['hour'] = df['timestamp'].dt.hour
    df['minute'] = df['timestamp'].dt.minute
    df['day_of_week'] = df['timestamp'].dt.dayofweek
    df['time_diff'] = df['timestamp'].diff().dt.total_seconds()
    
    # 计算用户行为长度
    df['user_behavior_length'] = len(activities)
    
    # 序列化数据
    cursor_time_seq = df['cursor_time'].fillna(-1).tolist()
    hour_seq = df['hour'].tolist()
    minute_seq = df['minute'].tolist()
    day_of_week_seq = df['day_of_week'].tolist()
    action_type_encoded_seq = df['action_type_encoded'].tolist()
    time_diff_seq = df['time_diff'].fillna(-1).tolist()
    user_behavior_length_seq = df['user_behavior_length'].tolist()
    source_encoded_seq = df['source_encoded'].tolist()
    user_answer_encoded_seq = df['user_answer_encoded'].fillna(-1).tolist()
    
    # 准备模型输入
    input_data = {
        'cursor_time_seq': cursor_time_seq,
        'hour_seq': hour_seq,
        'minute_seq': minute_seq,
        'day_of_week_seq': day_of_week_seq,
        'action_type_encoded_seq': action_type_encoded_seq,
        'time_diff_seq': time_diff_seq,
        'user_behavior_length_seq': user_behavior_length_seq,
        'source_encoded_seq': source_encoded_seq,
        'user_answer_encoded_seq': user_answer_encoded_seq
    }
    
    # 加载模型并进行预测
    try:
        model = torch.load('best_transformer_model_4.pth', map_location=torch.device('cpu'))
        model.eval()
        
        # 准备输入张量
        input_tensors = {}
        for k, v in input_data.items():
            input_tensors[k] = torch.tensor([v], dtype=torch.float32)
            
        # 进行预测
        with torch.no_grad():
            outputs = model(**input_tensors)
            prediction = 1 if outputs.item() > 0.5 else 0
        
        # 保存预测结果
        PredictionResult.objects.create(
            user_id=user_id,
            test_id=test_id,
            prediction=prediction
        )
        
        return JsonResponse({
            'status': 'success',
            'prediction': prediction
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })

@login_required
def student_records(request):
    if not request.user.is_staff:
        return redirect('login')  # 如果不是管理员，重定向到登录页面
    
    students = User.objects.filter(is_staff=False)
    selected_student_id = request.GET.get('student_id')
    
    predictions = []
    if selected_student_id:
        # 获取预测记录
        prediction_records = PredictionResult.objects.filter(user_id=selected_student_id).order_by('-timestamp')
        
        # 为每条记录添加试卷名称
        for record in prediction_records:
            # 尝试获取试卷名称
            test_name = "未知试卷"
            test_id = record.test_id
            
            if test_id.startswith('paper_'):
                # 如果是新格式的试卷ID (paper_X)，查询Test模型
                paper_id = test_id.replace('paper_', '')
                try:
                    paper = Test.objects.get(id=paper_id)
                    test_name = paper.title
                except Test.DoesNotExist:
                    pass
            else:
                # 对于旧格式的test_id，直接显示为"试卷-test_id"
                test_name = f"试卷-{test_id}"
            
            # 添加试卷名称到记录
            record.test_name = test_name
            predictions.append(record)
    
    return render(request, 'student_records.html', {
        'students': students,
        'selected_student_id': selected_student_id,
        'predictions': predictions
    })

def user_logout(request):
    logout(request)
    return redirect('login')
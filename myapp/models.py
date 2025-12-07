from django.db import models
from django.contrib.auth.models import User
# Create your models here.

class Test(models.Model):
    """试卷模型"""
    title = models.CharField(max_length=100, verbose_name="试卷标题")
    description = models.TextField(blank=True, verbose_name="试卷描述")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    
    def __str__(self):
        return self.title
    
    class Meta:
        verbose_name = "试卷"
        verbose_name_plural = "试卷"

class Question(models.Model):
    text = models.CharField(max_length=255, verbose_name="问题")
    option_a = models.CharField(max_length=100, verbose_name="选项 A")
    option_b = models.CharField(max_length=100, verbose_name="选项 B")
    option_c = models.CharField(max_length=100, verbose_name="选项 C")
    option_d = models.CharField(max_length=100, verbose_name="选项 D")
    correct_answer = models.CharField(max_length=1, choices=[
        ('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D')
    ], verbose_name="正确答案")
    test_id = models.CharField(max_length=50, verbose_name="试题ID", blank=True, null=True)
    paper = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='questions', null=True, blank=True, verbose_name="所属试卷")

    def __str__(self):
        return self.text
    
    def clean(self):
        """自定义清洗方法，确保数据有效性"""
        super().clean()
        # 如果有关联的试卷但没有test_id，生成test_id
        if self.paper and not self.test_id:
            if self.paper.id:  # 确保试卷已保存并有ID
                self.test_id = f"paper_{self.paper.id}"
            # 移除临时ID生成，让数据库使用默认值(null或空字符串)
        
    def save(self, *args, **kwargs):
        """重写save方法确保保存前设置正确的test_id"""
        # 如果有关联的试卷但没有test_id，生成test_id
        if self.paper and not self.test_id and self.paper.id:
            self.test_id = f"paper_{self.paper.id}"
        super().save(*args, **kwargs)
        
    class Meta:
        verbose_name = "问题"
        verbose_name_plural = "问题"

class Answer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, verbose_name="问题")
    user_answer = models.CharField(max_length=1, choices=[
        ('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D')
    ], verbose_name="用户答案")
    is_correct = models.BooleanField(verbose_name="是否正确")

    def __str__(self):
        return f"Question: {self.question.text}, Answer: {self.user_answer}"

class UserAction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    action_type = models.CharField(max_length=10, choices=[
        ('enter', 'Enter'),
        ('respond', 'Respond'),
        ('submit', 'Submit')
    ])
    test_id = models.CharField(max_length=50, default='', blank=True, verbose_name="试卷ID")  # 设置默认值为空字符串
    item_id = models.CharField(max_length=50, null=True, blank=True, verbose_name="题目ID")  # 添加item_id字段
    cursor_time = models.DurationField(null=True, blank=True)  # 允许为空
    source = models.CharField(max_length=10, choices=[
        ('diagnosis', 'Diagnosis'),
        ('archive', 'Archive'),
        ('sprint', 'Sprint')
    ])
    user_answer = models.CharField(max_length=10, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.action_type} - {self.test_id}"

class UserActivityFeature(models.Model):
    user_id = models.CharField(max_length=255, default='', blank=True)
    test_id = models.CharField(max_length=50, default='', blank=True)
    cursor_time_seq = models.FloatField(null=True)
    hour_seq = models.IntegerField(null=True)
    minute_seq = models.IntegerField(null=True)
    day_of_week_seq = models.IntegerField(null=True)
    action_type_encoded_seq = models.IntegerField(null=True)
    time_diff_seq = models.FloatField(null=True)
    is_exit_seq = models.BooleanField(default=False)
    user_behavior_length_seq = models.IntegerField(null=True)
    source_encoded_seq = models.IntegerField(null=True)
    user_answer_encoded_seq = models.IntegerField(null=True)

class PredictionResult(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    test_id = models.CharField(max_length=50)
    timestamp = models.DateTimeField(auto_now_add=True)
    prediction = models.IntegerField()  # 1表示需要提醒，0表示正常

    def __str__(self):
        return f"{self.user.username} - {self.test_id} - {self.timestamp}"

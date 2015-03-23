import datetime

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from api.utils import humanize_time
from django.db.models import Q
from notifications.models import Notification, NoticeType, queue
from accounts.models import UserProfile


class MuteList(models.Model):
    user = models.ForeignKey(User, null=False, blank=False)
    url = models.URLField(max_length=300, blank=False, null=True)
    word = models.URLField(max_length=300, blank=False, null=True)


class Tag(models.Model):
    user = models.ForeignKey(User, null=False, blank=False)
    name = models.CharField(max_length=80, blank=False, null=False)
    color = models.CharField(max_length=10, blank=False, null=False)
    domain = models.URLField(max_length=300, default='')


class ChatMessage(models.Model):
    author = models.ForeignKey(
        User, related_name='author', null=False, blank=False)
    message = models.CharField(max_length=2000, blank=False, null=False)
    date = models.DateTimeField(auto_now_add=True)
    url = models.URLField(max_length=300, blank=False, null=False)

    def __unicode__(self):
        return "Chat message item on %s by %s" % (self.date, self.author)


class FilterListItem(models.Model):
    user = models.ForeignKey(User, null=False, blank=False)
    url = models.URLField(max_length=200, null=False, blank=False)
    port = models.IntegerField(default=80)
    date_created = models.DateTimeField(default=datetime.datetime.utcnow())

    class Meta:
        abstract = True


class WhiteListItem(FilterListItem):

    class Meta:
        unique_together = ('user', 'url')

    def __unicode__(self):
        return "Whitelist item %s for %s" % (self.url, self.user.username)


class BlackListItem(FilterListItem):

    class Meta:
        unique_together = ('user', 'url')

    def __unicode__(self):
        return "Blacklist item %s for %s" % (self.url, self.user.username)


class EyeHistoryRaw(models.Model):
    user = models.ForeignKey(User)

    src = models.CharField(max_length=40, default='')
    url = models.URLField(max_length=2000, default='')
    domain = models.URLField(max_length=2000, default='')
    favicon_url = models.TextField(default='')
    favIconUrl = models.URLField(max_length=2000, default='')
    title = models.CharField(max_length=2000, default='')

    start_event = models.CharField(max_length=40, default='')
    start_time = models.DateTimeField()

    end_event = models.CharField(max_length=40, default='')
    end_time = models.DateTimeField()

    total_time = models.IntegerField()  # store in ms

    # store as human readable according to moment.js library:
    # http://momentjs.com/docs/#/displaying/humanize-duration/
    humanize_time = models.CharField(max_length=200, default='')

    def __unicode__(self):
        return "EyeHistory item %s for %s on %s" % (
            self.url, self.user.username, self.start_time)


class EyeHistory(models.Model):
    user = models.ForeignKey(User)

    src = models.CharField(max_length=40, default='')
    url = models.URLField(max_length=2000, default='')
    domain = models.URLField(max_length=2000, default='')
    favicon_url = models.TextField(default='')
    favIconUrl = models.URLField(max_length=2000, default='')
    title = models.CharField(max_length=2000, default='')

    start_event = models.CharField(max_length=40, default='')
    start_time = models.DateTimeField()

    end_event = models.CharField(max_length=40, default='')
    end_time = models.DateTimeField()

    total_time = models.IntegerField()  # store in ms

    # store as human readable according to moment.js library:
    # http://momentjs.com/docs/#/displaying/humanize-duration/
    humanize_time = models.CharField(max_length=200, default='')

    def __unicode__(self):
        return "EyeHistory item %s for %s on %s" % (
            self.url, self.user.username, self.start_time)


class EyeHistoryMessage(models.Model):
    message = models.CharField(max_length=300, default='')
    post_time = models.DateTimeField(auto_now_add=True)
    eyehistory = models.ForeignKey(
        EyeHistory, blank=True, null=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ['-post_time']

    def __unicode__(self):
        return "Message %s on %s" % (self.message, self.post_time)


class PopularHistoryInfo(models.Model):
    url = models.URLField(max_length=255, unique=True)

    img_url = models.URLField(max_length=2000, default='')
    description = models.TextField(default='')

    domain = models.URLField(max_length=100, default='')
    favicon_url = models.TextField(default='')
    favIconUrl = models.URLField(max_length=2000, default='')
    title = models.CharField(max_length=2000, default='')


class PopularHistory(models.Model):

    user = models.ForeignKey(User, null=True)

    popular_history = models.ForeignKey(PopularHistoryInfo, null=False)
    eye_hists = models.ManyToManyField(EyeHistory)
    visitors = models.ManyToManyField(User, related_name='pophist_visitors')
    messages = models.ManyToManyField(EyeHistoryMessage)
    # unique visitors + avg_time_spent + num_comments / avg_time_ago
    top_score = models.FloatField(default=0.0)
    # unique visitors / avg_time_ago
    unique_visitor_score = models.FloatField(default=0.0)
    # avg_time_spent / avg_time_ago
    avg_time_spent_score = models.FloatField(default=0.0)
    # avg_time_spent / avg_time_ago
    num_comment_score = models.FloatField(default=0.0)

    total_time_spent = models.IntegerField(default=0)    # store in ms
    total_time_ago = models.IntegerField(default=0)    # store in rounded hours

    humanize_avg_time = models.CharField(max_length=200, default='')
    avg_time_ago = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "popular_history")


def save_raw_eyehistory(user, url, title,
                        start_event, end_event,
                        start_time, end_time,
                        src, domain, favicon_url):
    elapsed_time = end_time - start_time
    total_time = int(round((elapsed_time.microseconds / 1.0E3) +
                           (elapsed_time.seconds * 1000) +
                           (elapsed_time.days * 8.64E7)))
    hum_time = humanize_time(elapsed_time)

    raw, created = EyeHistoryRaw.objects.get_or_create(user=user,
                                                       url=url,
                                                       title=title,
                                                       start_event=start_event,
                                                       end_event=end_event,
                                                       start_time=start_time,
                                                       end_time=end_time,
                                                       src=src,
                                                       domain=domain,
                                                       favicon_url=favicon_url,
                                                       total_time=total_time,
                                                       humanize_time=hum_time)


def merge_histories(dup_histories, end_time, end_event):
    earliest_start = timezone.now()
    earliest_eyehist = None
    dup_histories = list(dup_histories)

    for hist in dup_histories:
        if hist.start_time < earliest_start:
            earliest_start = hist.start_time
            earliest_eyehist = hist

    if earliest_eyehist is None:
        earliest_eyehist = dup_histories[0]

    earliest_eyehist.end_time = end_time
    earliest_eyehist.end_event = end_event

    elapsed_time = earliest_eyehist.end_time - earliest_eyehist.start_time
    earliest_eyehist.total_time = int(round(
        (elapsed_time.microseconds / 1.0E3)
        + (elapsed_time.seconds * 1000) +
        (elapsed_time.days * 8.64E7)))
    earliest_eyehist.humanize_time = humanize_time(elapsed_time)

    earliest_eyehist.save()

    if len(dup_histories) > 1:
        for item in dup_histories:
            if item != earliest_eyehist:
                messages = EyeHistoryMessage.objects.filter(eyehistory=item)
                for message in messages:
                    message.eyehistory = earliest_eyehist
                    message.save()
                item.delete()

    return earliest_eyehist

def check_bumps(user, start_time, end_time, url):
    earlier_time = start_time - datetime.timedelta(minutes=5)
    later_time = end_time + datetime.timedelta(minutes=5)
    bumps = EyeHistory.objects.filter(url=url & ~Q(user=user) & (Q(end_time__gte=earlier_time) | Q(start_time__lte=later_time)))
    if bumps.count() > 0:
        user_prof = UserProfile.objects.get(user=user)
        n = NoticeType.objects.get(label="bump_follower")
        for bump in bumps:
            bump_prof = UserProfile.objects.get(user=bump.user)
            if bump_prof in user_prof.follows.all():
                Notification.objects.create(recipient=user, notice_type=n, sender=bump.user, url=url)
                queue([user], "bump_follower", sender=bump.user, extra_content={'url': url,
                                                                                   'date': datetime.datetime.now()})
            if user_prof in bump_prof.follows.all():
                Notification.objects.create(recipient=bump.user, notice_type=n, sender=user, url=url)
                queue([bump.user], "bump_follower", sender=user, extra_content={'url': url,
                                                                                   'date': datetime.datetime.now()})
                
            
    
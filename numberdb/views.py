from django.shortcuts import render, get_object_or_404

from django.http import HttpResponse, HttpResponseRedirect

'''
#def index(request):
#    return HttpResponse("ello, world. You're at the chat index.")
    
def index(request):
    #latest_question_list = Question.objects.order_by('-pub_date')[:5]
    context = {
        'blub': 0,
    }
    #print("request:",request.user.__dir__())
    #template = loader.get_template('polls/index.html')
    #return HttpResponse(template.render(context, request))
    return render(request,'numberdb/index.html',context)
'''

def maintenance_in_progress(request):
    return HttpResponse("Maintenance in progress.")

def in_development(request):
    return HttpResponse("This database is currently in development.")

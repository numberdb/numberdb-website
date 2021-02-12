from django.shortcuts import render, get_object_or_404

from django.http import HttpResponse, HttpResponseRedirect


def maintenance_in_progress(request):
    return HttpResponse("Maintenance in progress.")

def in_development(request):
    return HttpResponse("This database is currently in development.")

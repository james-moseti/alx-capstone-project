from django.shortcuts import render

from django.http import HttpResponse

def products_home(request):
    return HttpResponse("Products Home Page")

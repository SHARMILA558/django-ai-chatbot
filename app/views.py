import json
from groq import Groq
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from .models import Conversation, Message



api_key = settings.GROQ_API_KEY

def chat_view(request):
    if not api_key:
        return JsonResponse(
            {"error": "API key not configured"},
            status=500
        )

def index(request):
    conversations = Conversation.objects.all()
    return render(request, 'chat/index.html', {'conversations': conversations})


def conversation_detail(request, conversation_id):
    conversation = get_object_or_404(Conversation, id=conversation_id)
    conversations = Conversation.objects.all()
    messages = conversation.messages.all()
    return render(request, 'chat/index.html', {
        'conversations': conversations,
        'active_conversation': conversation,
        'messages': messages,
    })


@csrf_exempt
@require_http_methods(["POST"])
def new_conversation(request):
    conversation = Conversation.objects.create()
    return JsonResponse({'id': str(conversation.id), 'title': conversation.title})


@csrf_exempt
@require_http_methods(["DELETE"])
def delete_conversation(request, conversation_id):
    conversation = get_object_or_404(Conversation, id=conversation_id)
    conversation.delete()
    return JsonResponse({'success': True})


@csrf_exempt
@require_http_methods(["POST"])
def send_message(request, conversation_id):
    # Check API key first
    if not settings.GROQ_API_KEY:
        return JsonResponse({
            'error': 'GROQ_API_KEY is not set. Please set it in your environment or settings.py.'
        }, status=500)

    conversation = get_object_or_404(Conversation, id=conversation_id)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON in request body'}, status=400)

    user_content = data.get('message', '').strip()

    if not user_content:
        return JsonResponse({'error': 'Message cannot be empty'}, status=400)

    # Save user message
    Message.objects.create(conversation=conversation, role='user', content=user_content)

    # Update conversation title if it's the first message
    if conversation.title == 'New Chat' and conversation.messages.count() == 1:
        title = user_content[:50] + ('...' if len(user_content) > 50 else '')
        conversation.title = title
        conversation.save()

    # Build messages history for API
    all_messages = [
        {'role': msg.role, 'content': msg.content}
        for msg in conversation.messages.all()
    ]

    def stream_chat_response():
  
        full_response = ""
        try:
            client = Groq(api_key=settings.GROQ_API_KEY)
            completion = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=all_messages,
                temperature=1,
                max_completion_tokens=1024,
                top_p=1,
                stream=True,
            #stop=None,
            )

            for chunk in completion:
                text = chunk.choices[0].delta.content or ""
                if text:
                    full_response += text
                    yield f"data: {json.dumps({'chunk': text})}\n\n"

        # Save assistant message after streaming completes
            Message.objects.create(
                conversation=conversation,
                role='assistant',
                content=full_response
            )
               # conversation.save()
            yield f"data: {json.dumps({'done': True, 'title': conversation.title})}\n\n"

        except Exception as e:
            import traceback
        print("========== GROQ ERROR ==========")
        traceback.print_exc()
        print("================================")
        yield f"data: {json.dumps({'error': str(e)})}\n\n"
    # ✅ VERY IMPORTANT PART
    response = StreamingHttpResponse(
        stream_chat_response(),
        content_type="text/event-stream"
    )

    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"

    return response


def chat_view(request, conversation_id):
    """
    Django view to handle streaming chat responses.
    """
    # Fetch your conversation object and messages
    conversation = Conversation.objects.get(id=conversation_id)
    all_messages = Message.objects.filter(conversation=conversation).values('role', 'content')

    response = StreamingHttpResponse(stream_chat_response(conversation, all_messages),
                                     content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


def get_conversations(request):
    """
    Django view to fetch all conversations.
    """
    conversations = Conversation.objects.all().values('id', 'title', 'updated_at')
    return JsonResponse({'conversations': list(conversations)})
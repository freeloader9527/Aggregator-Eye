import time

socketio_instance = None

def init_logger(sio):
    global socketio_instance
    socketio_instance = sio

def debug_log(msg, color='white'):
    timestamp = time.strftime("%H:%M:%S")
    out_msg = f"[{timestamp}] {msg}"
    print(out_msg)
    if socketio_instance:
        try:
            socketio_instance.emit('log', {'time': timestamp, 'msg': msg, 'color': color})
            time.sleep(0.01)
        except Exception as e:
            pass # Ignore if no client or context error

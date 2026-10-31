"""Finite synthetic provider/media; never loaded by the production application."""
import io
import json
import struct
import wave
import zlib


def png(color=0):
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind+data) & 0xffffffff)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB',128,64,8,2,0,0,0)) + chunk(b'IDAT',zlib.compress((b'\x00'+bytes([color,180,160])*128)*64)) + chunk(b'IEND',b'')


def wav():
    result = io.BytesIO()
    with wave.open(result, 'wb') as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(8000)
        audio.writeframes(b'\x00\x00' * 800)
    return result.getvalue()


class Provider:
    def __init__(self):
        self.calls = []
        self.fail = None

    def brief(self, project):
        self.calls.append('brief')
        return {'summary':'Dữ liệu kiểm thử tổng hợp, không phải bất động sản thật.',
                'facts':[{'text':'Thông tin mẫu','provenance':'verified','source':'description'}], 'missing':[]}

    def observe(self, project, asset, content):
        self.calls.append('observe')
        if self.fail == 'observe':
            self.fail = None
            raise ValueError('private-upstream-error')
        return {'label':asset['name'], 'room_type':'test', 'summary':'Ảnh kiểm thử tổng hợp.',
                'facts':[{'text':'Màu kiểm thử','provenance':'observed','source':asset['id']}], 'uncertainty':['Chưa có kích thước.']}

    def script(self, project, rooms, brief):
        self.calls.append('script')
        return {'introduction':'Đây là tour fixture.', 'segments':[
            {'checkpoint_id':r['checkpoint_id'], 'text':'Lời kiểm thử '+r['label'], 'sources':[r['asset_id']]}
            for r in rooms]}

    def speech(self, project, text):
        self.calls.append('speech')
        return wav()

    def answer(self, package, question, checkpoint_id):
        self.calls.append('answer')
        return {'text':'Thông tin chỉ đọc từ tour fixture đã duyệt.', 'navigate_to':None}

    def edit(self, state, text):
        self.calls.append('edit')
        if not state.get('script'):
            return {'reply':'Đề xuất đổi tên checkpoint từ fixture.',
                    'rooms':[{'checkpoint_id':state['rooms'][0]['checkpoint_id'],
                              'label':'Phòng khách mới fixture','summary':None,'yaw':None}],
                    'scripts':[], 'introduction':None, 'order':None, 'connections':None}
        return {'reply':'Đề xuất đổi lời giới thiệu đầu tiên từ fixture.', 'rooms':[],
                'scripts':[{**state['script']['segments'][0], 'text':'Lời mới đã được Business yêu cầu.'}],
                'introduction':None, 'order':None, 'connections':None}


class Worker:
    def build(self, project, rooms, connections, assets):
        # Valid triangle GLB; this is a worker fixture, not house reconstruction.
        raw=struct.pack('<9f',0,0,0,1,0,0,0,1,0)
        data={'asset':{'version':'2.0'}, 'scene':0,'scenes':[{'nodes':[0]}],
              'nodes':[{'mesh':0}], 'meshes':[{'primitives':[{'attributes':{'POSITION':0}}]}],
              'buffers':[{'byteLength':len(raw)}], 'bufferViews':[{'buffer':0,'byteLength':len(raw)}],
              'accessors':[{'bufferView':0,'componentType':5126,'count':3,'type':'VEC3','min':[0,0,0],'max':[1,1,0]}]}
        encoded=json.dumps(data).encode()
        encoded+=b' '*((-len(encoded))%4)
        glb=b'glTF'+struct.pack('<II',2,28+len(encoded)+len(raw))+struct.pack('<II',len(encoded),0x4e4f534a)+encoded+struct.pack('<II',len(raw),0x004e4942)+raw
        return {'glb':glb,'anchors':{r['checkpoint_id']:{'position':[i,0,0],'room_id':r['room_id']} for i,r in enumerate(rooms)}}

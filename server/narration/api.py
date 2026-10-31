"""Hook on the existing /api/tours router; owner/Origin policy stays caller-owned."""
from fastapi import Request
from .models import Generate, Attach
from .provider import VOICES
from .service import NarrationService


def install_narration(router, db, owner, draft, check_revision, validate_doc, data_root, env,
                      *, object_storage=None, storage_guard=None, provider=None, clock=None):
    options={'clock':clock} if clock is not None else {}
    service=NarrationService(env,data_root,db=db,draft=draft,check_revision=check_revision,
        validate_doc=validate_doc,object_storage=object_storage,storage_guard=storage_guard,provider=provider,**options)

    @router.get('/narration/config')
    def config(request:Request):
        owner(request)
        return {'configured':service.configured,'locales':['en','vi'],'voices':list(VOICES),
                'max_script_chars':service.max_chars,'model':service.model,
                'reason':None if service.configured else 'NARRATION_ENABLED / OPENAI_TTS_API_KEY',
                'deprecation_date':'2027-01-06'}

    @router.post('/narration/jobs',status_code=202)
    def submit(data:Generate,request:Request):return service.submit(data,owner(request))

    @router.get('/narration/jobs/{id}')
    def status(id:str,request:Request):return service.get(id,owner(request))

    @router.post('/narration/jobs/{id}/cancel')
    def cancel(id:str,request:Request):return service.cancel(id,owner(request))

    @router.post('/narration/jobs/{id}/attach')
    def attach(id:str,data:Attach,request:Request):return service.attach(id,owner(request),data.revision)

    return service

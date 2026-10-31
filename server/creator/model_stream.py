"""Stream only public reasoning summaries and an unvalidated plan preview."""
import time
import jiter


def stream_plan(client, kwargs, progress=None):
    started=time.monotonic()
    last_emit=0.0
    summary=''
    output=''
    state={'model':kwargs['model'], 'effort':kwargs['reasoning']['effort'],
           'started_at':time.time()*1000, 'phase':'connecting', 'reasoning_summary':'', 'plan_preview':{}, 'output_characters':0}

    def publish(force=False):
        nonlocal last_emit
        now=time.monotonic()
        if progress and (force or now-last_emit>=.75):
            last_emit=now
            state['elapsed_seconds']=round(now-started)
            progress(dict(state))

    publish(True)
    # summary=auto requests the most detailed public summary supported by the model.
    kwargs['reasoning']={**kwargs['reasoning'],'summary':'auto'}
    with client.responses.stream(**kwargs) as stream:
        for event in stream:
            kind=event.type
            if kind=='response.created':
                state['phase']='thinking';publish(True)
            elif kind=='response.reasoning_summary_part.added':
                if summary: summary+='\n\n'
            elif kind=='response.reasoning_summary_text.delta':
                summary=(summary+event.delta)[:24000]
                state.update(phase='thinking',reasoning_summary=summary)
                publish()
            elif kind=='response.reasoning_summary_text.done':
                publish(True)
            elif kind=='response.output_text.delta':
                output+=event.delta
                preview={}
                try:
                    partial=jiter.from_json(output.encode(),partial_mode='trailing-strings')
                    if isinstance(partial,dict):
                        preview={'summary':str(partial.get('summary',''))[:1500],
                            'spaces':[s.get('label','') for s in partial.get('spaces',[]) if isinstance(s,dict)],
                            'captures':len(partial.get('captures',[])),
                            'fixtures':len(partial.get('fixtures',[]))}
                except (ValueError,TypeError): pass
                state.update(phase='writing_plan',plan_preview=preview,output_characters=len(output))
                publish()
            # Deliberately do not forward reasoning_text, encrypted content, prompts or tool payloads.
        response=stream.get_final_response()
    state['phase']='validating';publish(True)
    return response

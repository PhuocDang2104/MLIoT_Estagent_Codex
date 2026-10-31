"""Read-only LangGraph adapter for the existing TourReply contract."""
from typing import TypedDict
from langgraph.graph import StateGraph,START,END
from server.tours.models import TourReply

class State(TypedDict,total=False):
    context:dict
    result:dict

def build_graph(answer):
    def respond(state):return {'result':TourReply.model_validate(answer(state['context'])).model_dump()}
    def validate(state):
        result=state['result'];context=state['context'];ids={s['id'] for s in context['tour']['scenes']}
        if result['changes'] or result['order'] is not None:raise ValueError('Viewer cannot edit the tour')
        if result['start_scene_id'] is not None and result['start_scene_id'] not in ids:raise ValueError('Unknown navigation target')
        if not result['reply'].strip() or len(result['reply'])>800:raise ValueError('Reply must contain 1–800 characters')
        return {'result':result}
    graph=StateGraph(State);graph.add_node('grounded_answer',respond);graph.add_node('validate_read_only',validate)
    graph.add_edge(START,'grounded_answer');graph.add_edge('grounded_answer','validate_read_only');graph.add_edge('validate_read_only',END)
    return graph.compile()

"""Export real StateGraph edges, a Business view, and the requested local copies.

No graph execution, model request, remote renderer, or application secrets.
Run with the existing pinned backend requirements. Mermaid is validated separately.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from langchain_core.runnables.graph import Edge, Graph, NodeStyles
from langgraph.checkpoint.memory import MemorySaver
from server.creator.graph import build_graph

FOLDER = ROOT / 'docs/Business Workflow Langgraph'
STEM = 'Estagent_Business_LangGraph'
LABELS = {
    '__start__': 'START',
    'understand': 'understand<br/>OpenAI · trích xuất hồ sơ',
    'scene': 'scene<br/>OpenAI Vision · từng ảnh',
    'spatial': 'spatial<br/>Tạo room / checkpoint nháp',
    'spatial_review': 'spatial_review<br/>interrupt · Business kiểm tra',
    'build_model': 'build_model<br/>Adapter dựng 3D',
    'mapping': 'mapping<br/>Kiểm tra room / anchor',
    'semantic': 'semantic<br/>Giữ dữ kiện có nguồn',
    'navigation': 'navigation<br/>Hotspots + hành trình hợp lệ',
    'narration': 'narration<br/>OpenAI · viết lời giới thiệu',
    'final_review': 'final_review<br/>interrupt · Duyệt lời giới thiệu',
    'voice': 'voice<br/>OpenAI TTS · từng đoạn',
    'assemble': 'assemble<br/>Kiểm tra và đóng gói',
    '__end__': 'END',
}
ROUTES = {
    ('scene', 'scene'): 'Còn ảnh', ('scene', 'spatial'): 'Đủ ảnh',
    ('spatial_review', 'build_model'): 'Duyệt', ('spatial_review', '__end__'): 'Từ chối',
    ('final_review', 'voice'): 'Duyệt', ('final_review', '__end__'): 'Từ chối',
    ('voice', 'voice'): 'Còn đoạn', ('voice', 'assemble'): 'Đủ audio',
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--downloads-dir', type=Path, help='explicit user-requested output directory')
    args = parser.parse_args()
    compiled = build_graph(None, MemorySaver(), lambda *a: None, lambda *a: None,
                           lambda *a: None, lambda *a: None)
    visualization = compiled.get_graph()
    # The pinned get_graph() visualizer folds conditional END edges incorrectly.
    # Read the StateGraph declarations so both reject routes remain visible.
    edges = [Edge(source, target) for source, target in sorted(compiled.builder.edges)]
    for source, branches in compiled.builder.branches.items():
        for branch in branches.values():
            if branch.ends is None:
                raise ValueError(f'Explicit path_map required for {source}')
            edges.extend(Edge(source, target, conditional=True) for target in sorted(set(branch.ends.values())))
    graph = Graph(nodes=visualization.nodes, edges=edges)
    unknown = set(graph.nodes) - LABELS.keys()
    if unknown:
        raise ValueError(f'Add Business labels for new graph nodes: {sorted(unknown)}')
    native = graph.draw_mermaid(node_colors=NodeStyles(
        default='fill:#fafafa,stroke:#dedee1,color:#292c2e',
        first='fill:#fff0eb,stroke:#ed321e,color:#292c2e',
        last='fill:#292c2e,stroke:#292c2e,color:#ffffff',
    ), frontmatter_config={'config': {'theme': 'base', 'themeVariables': {
        'fontFamily': 'Manrope, Arial, sans-serif', 'lineColor': '#81848a',
        'fontSize': '13px', 'primaryTextColor': '#292c2e',
        'primaryColor': '#fafafa', 'secondaryColor': '#ededed',
        'tertiaryColor': '#fafafa', 'edgeLabelBackground': '#fafafa',
        'clusterBkg': '#ffffff', 'clusterBorder': '#dedee1',
    }}})
    (FOLDER / f'{STEM}_StateGraph.mmd').write_text(native.rstrip() + '\n', encoding='utf8')
    init = {'theme': 'base', 'themeVariables': {'fontFamily': 'Manrope, Arial, sans-serif',
            'fontSize': '13px', 'lineColor': '#96999e', 'primaryTextColor': '#292c2e',
            'primaryColor': '#fafafa', 'secondaryColor': '#ededed',
            'tertiaryColor': '#fafafa', 'edgeLabelBackground': '#fafafa',
            'clusterBkg': '#ffffff', 'clusterBorder': '#dedee1'},
            'flowchart': {'curve': 'basis', 'nodeSpacing': 30, 'rankSpacing': 42}}
    lines = ['%% Generated from server/creator/graph.py by scripts/export_studio_graph.py.',
             '%% Solid edges inside LG are actual StateGraph edges. Dotted edges describe API/status boundaries.',
             '%%{init: ' + json.dumps(init) + '}%%', 'flowchart TB',
             '    INPUT["Business · ảnh + mô tả + tùy chọn"]:::boundary',
             '    API["FastAPI · validate / upload / tạo generation"]:::boundary',
             '    QUEUED["queued · trả 202, chạy nền"]:::boundary',
             '    INPUT -.-> API -.-> QUEUED',
             '    subgraph LG["LANGGRAPH STATEGRAPH · RUNTIME HIỆN TẠI"]']
    for name in graph.nodes:
        kind = ('terminal' if name in ('__start__', '__end__') else 'review'
                if name in ('spatial_review', 'final_review') else 'worker'
                if name == 'build_model' else 'node')
        lines.append(f'        {name}["{LABELS[name]}"]:::{kind}')
    for edge in graph.edges:
        label = ROUTES.get((edge.source, edge.target))
        arrow = f'-->|"{label}"|' if label else '-->'
        lines.append(f'        {edge.source} {arrow} {edge.target}')
    lines.extend([
        '    end',
        '    QUEUED -.-> __start__',
        '    WAIT["waiting_integration<br/>Chưa có adapter · Không publish"]:::waiting',
        '    build_model -. "interrupt khi thiếu worker" .-> WAIT',
        '    WAIT -. "Retry khi adapter sẵn sàng" .-> build_model',
        '    FAILED["failed · giữ checkpoint đã hoàn tất"]:::waiting',
        '    LG -. "Exception / process dừng lúc đang chạy" .-> FAILED',
        '    FAILED -. "Retry có giới hạn tại node đang dở" .-> LG',
        '    REJECTED["rejected · Không publish"]:::waiting',
        '    READY["completed · Bản nháp đủ tài sản"]:::boundary',
        '    __end__ -. "rejected = true" .-> REJECTED',
        '    __end__ -. "package + approved" .-> READY',
        '    PUBLISH["Business chọn xuất bản<br/>API kiểm approval + music + assets"]:::review',
        '    SNAPSHOT["Snapshot bất biến"]:::terminal',
        '    VIEWER["Viewer · ảnh / 360° + audio<br/>GLB download · OpenAI Q&A chỉ đọc"]:::boundary',
        '    READY -.-> PUBLISH -.-> SNAPSHOT -.-> VIEWER',
        '    classDef node fill:#fafafa,stroke:#d4d6da,color:#292c2e,stroke-width:1px;',
        '    classDef review fill:#fff0eb,stroke:#ed321e,color:#8c3428,stroke-width:1.5px;',
        '    classDef worker fill:#eeeef0,stroke:#81848a,color:#292c2e,stroke-width:1.5px;',
        '    classDef terminal fill:#292c2e,stroke:#292c2e,color:#ffffff,stroke-width:1.5px;',
        '    classDef boundary fill:#f3f3f4,stroke:#bfc2c7,color:#63656b,stroke-width:1px;',
        '    classDef waiting fill:#fafafa,stroke:#bfc2c7,color:#7a7d82,stroke-width:1px,stroke-dasharray:4 4;',
        '    style LG fill:#ffffff,stroke:#d4d6da,color:#292c2e',
    ])
    business = '\n'.join(lines) + '\n'
    primary = FOLDER / f'{STEM}_Flow.mmd'
    primary.write_text(business, encoding='utf8')
    markdown = FOLDER / f'{STEM}_Flow.md'
    text = markdown.read_text(encoding='utf8')
    text, count = re.subn(r'<!-- runtime-graph:start -->.*?<!-- runtime-graph:end -->',
        '<!-- runtime-graph:start -->\n```mermaid\n' + business + '```\n<!-- runtime-graph:end -->',
        text, flags=re.S)
    if count != 1:
        raise ValueError('Markdown must have exactly one runtime graph marker pair')
    markdown.write_text(text, encoding='utf8')
    evidence = ROOT / 'tests/ai/evidence/studio-refinement'
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / 'graph-export.json').write_text(json.dumps({
        'node_ids': list(graph.nodes), 'edges': [dict(source=e.source, target=e.target,
        conditional=e.conditional) for e in graph.edges],
        'graph_source_sha256': hashlib.sha256((ROOT/'server/creator/graph.py').read_bytes()).hexdigest(),
        'source': 'StateGraph.builder.edges + branches.ends; Graph.draw_mermaid()',
        'compiled_visualization_edges': [dict(source=e.source,target=e.target) for e in visualization.edges],
        'executed': False,
        'live_api_calls': 0,
    }, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    if args.downloads_dir:
        folder = args.downloads_dir.resolve(strict=True)
        destination = folder / primary.name
        reference = folder / f'{STEM}_Flow.reference.mmd'
        if destination.exists() and not reference.exists():
            shutil.copy2(destination, reference)
        for path in [primary, markdown, FOLDER / f'{STEM}_StateGraph.mmd']:
            shutil.copy2(path, folder/path.name)
    print(f'Exported {len(graph.nodes)} nodes / {len(graph.edges)} edges; no graph execution or API calls')


if __name__ == '__main__':
    main()

import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import './KnowledgeGraph.css';
import { ConceptDetailPanel } from './ConceptDetailPanel';

interface ConceptNode extends d3.SimulationNodeDatum {
  id: string;
  title: string;
  description: string;
  tags: string[];
  path: string;
}

interface ConceptEdge extends d3.SimulationLinkDatum<ConceptNode> {
  source: string | ConceptNode;
  target: string | ConceptNode;
}

interface KnowledgeGraphProps {
  apiUrl: string;
  token: string | null;
  topicId: string;
}

export const KnowledgeGraph: React.FC<KnowledgeGraphProps> = ({ apiUrl, token, topicId }) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [nodes, setNodes] = useState<ConceptNode[]>([]);
  const [links, setLinks] = useState<ConceptEdge[]>([]);
  const [selectedNode, setSelectedNode] = useState<ConceptNode | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchGraph = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch(`${apiUrl}/api/knowledge/${topicId}/graph`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        if (res.status === 404) {
          setError('No knowledge graph found. Run a web search ingestion first.');
        } else {
          setError('Failed to fetch knowledge graph');
        }
        return;
      }
      const data = await res.json();
      setNodes(data.nodes);
      setLinks(data.edges);
    } catch (err) {
      setError('Network error loading knowledge graph');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchGraph();
  }, [apiUrl, token, topicId]);

  useEffect(() => {
    if (!nodes.length || !svgRef.current || !containerRef.current) return;

    const width = containerRef.current.clientWidth;
    const height = 600;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove(); // Clear previous render

    svg.attr('viewBox', [0, 0, width, height].join(' '));

    // Define arrowhead marker
    svg
      .append('defs')
      .append('marker')
      .attr('id', 'arrowhead')
      .attr('viewBox', '-0 -5 10 10')
      .attr('refX', 20)
      .attr('refY', 0)
      .attr('orient', 'auto')
      .attr('markerWidth', 8)
      .attr('markerHeight', 8)
      .attr('xoverflow', 'visible')
      .append('svg:path')
      .attr('d', 'M 0,-5 L 10 ,0 L 0,5')
      .attr('fill', '#999')
      .style('stroke', 'none');

    const simulation = d3
      .forceSimulation<ConceptNode>(nodes)
      .force(
        'link',
        d3
          .forceLink<ConceptNode, ConceptEdge>(links)
          .id(d => d.id)
          .distance(100)
      )
      .force('charge', d3.forceManyBody().strength(-300))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collide', d3.forceCollide().radius(50));

    // Create a main group for zoom
    const g = svg.append('g').attr('class', 'main-group');

    const zoom = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.1, 4])
      .on('zoom', event => {
        g.attr('transform', event.transform);
      });

    svg.call(zoom);

    const link = g
      .append('g')
      .attr('class', 'links')
      .selectAll('line')
      .data(links)
      .enter()
      .append('line')
      .attr('class', 'link')
      .attr('stroke', 'rgba(255,255,255,0.2)')
      .attr('stroke-width', 1.5)
      .attr('marker-end', 'url(#arrowhead)');

    const node = g
      .append('g')
      .attr('class', 'nodes')
      .selectAll('g')
      .data(nodes)
      .enter()
      .append('g')
      .attr('class', 'node')
      .call(
        d3
          .drag<SVGGElement, ConceptNode, ConceptNode>()
          .on('start', dragstarted)
          .on('drag', dragged)
          .on('end', dragended)
      )
      .on('click', (event, d) => setSelectedNode(d));

    node
      .append('circle')
      .attr('r', 18)
      .attr('fill', 'var(--accent-primary)')
      .attr('stroke', 'var(--accent-secondary)')
      .attr('stroke-width', 2)
      .style('filter', 'drop-shadow(0 0 8px rgba(99, 102, 241, 0.4))');

    node
      .append('text')
      .attr('dy', 32)
      .attr('text-anchor', 'middle')
      .text(d => d.title)
      .attr('fill', 'var(--text-primary)')
      .style('font-size', '12px')
      .style('font-weight', '500')
      .style('pointer-events', 'none')
      .attr('class', 'node-label');

    simulation.on('tick', () => {
      link
        .attr('x1', d => (d.source as ConceptNode).x!)
        .attr('y1', d => (d.source as ConceptNode).y!)
        .attr('x2', d => (d.target as ConceptNode).x!)
        .attr('y2', d => (d.target as ConceptNode).y!);

      node.attr('transform', d => `translate(${d.x},${d.y})`);
    });

    function dragstarted(
      event: d3.D3DragEvent<SVGGElement, ConceptNode, ConceptNode>,
      d: ConceptNode
    ) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      d.fx = d.x;
      d.fy = d.y;
    }

    function dragged(event: d3.D3DragEvent<SVGGElement, ConceptNode, ConceptNode>, d: ConceptNode) {
      d.fx = event.x;
      d.fy = event.y;
    }

    function dragended(
      event: d3.D3DragEvent<SVGGElement, ConceptNode, ConceptNode>,
      d: ConceptNode
    ) {
      if (!event.active) simulation.alphaTarget(0);
      d.fx = null;
      d.fy = null;
    }

    // Add explicit zoom controls
    d3.select(containerRef.current).select('.zoom-controls').remove();
    const controls = d3
      .select(containerRef.current)
      .append('div')
      .attr('class', 'zoom-controls')
      .style('position', 'absolute')
      .style('bottom', '20px')
      .style('right', '20px')
      .style('display', 'flex')
      .style('gap', '8px');

    controls
      .append('button')
      .text('+')
      .style('width', '32px')
      .style('height', '32px')
      .style('border-radius', '50%')
      .style('background', 'var(--bg-tertiary)')
      .style('border', '1px solid var(--border-color)')
      .style('color', 'var(--text-primary)')
      .style('cursor', 'pointer')
      .on('click', () => svg.transition().call(zoom.scaleBy, 1.3));
    controls
      .append('button')
      .text('-')
      .style('width', '32px')
      .style('height', '32px')
      .style('border-radius', '50%')
      .style('background', 'var(--bg-tertiary)')
      .style('border', '1px solid var(--border-color)')
      .style('color', 'var(--text-primary)')
      .style('cursor', 'pointer')
      .on('click', () => svg.transition().call(zoom.scaleBy, 0.7));
    controls
      .append('button')
      .text('⟲')
      .style('width', '32px')
      .style('height', '32px')
      .style('border-radius', '50%')
      .style('background', 'var(--bg-tertiary)')
      .style('border', '1px solid var(--border-color)')
      .style('color', 'var(--text-primary)')
      .style('cursor', 'pointer')
      .on('click', () => svg.transition().call(zoom.transform, d3.zoomIdentity));

    return () => {
      simulation.stop();
    };
  }, [nodes, links]);

  if (isLoading) {
    return (
      <div style={{ padding: '32px', textAlign: 'center', color: 'var(--text-secondary)' }}>
        Loading knowledge graph...
      </div>
    );
  }

  if (error) {
    return <div style={{ padding: '32px', textAlign: 'center', color: '#ef4444' }}>{error}</div>;
  }

  return (
    <div
      className="glass-card"
      style={{
        display: 'flex',
        height: '600px',
        borderRadius: '12px',
        overflow: 'hidden',
        border: '1px solid var(--border-color)',
        background: 'var(--bg-primary)',
      }}
    >
      <div style={{ flex: 1, position: 'relative' }} ref={containerRef}>
        <svg
          ref={svgRef}
          style={{ width: '100%', height: '100%', cursor: 'grab', display: 'block' }}
        />
        <div
          style={{
            position: 'absolute',
            top: '16px',
            left: '16px',
            background: 'rgba(19, 27, 46, 0.8)',
            padding: '12px 16px',
            borderRadius: '8px',
            border: '1px solid var(--border-color)',
            backdropFilter: 'blur(8px)',
          }}
        >
          <h3
            style={{
              fontWeight: 600,
              color: 'var(--text-primary)',
              margin: 0,
              marginBottom: '4px',
            }}
          >
            Knowledge Graph
          </h3>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', margin: 0 }}>
            Scroll or pinch to zoom. Drag nodes to explore. Click to read.
          </p>
        </div>
      </div>
      {selectedNode && (
        <div
          style={{
            width: '400px',
            borderLeft: '1px solid var(--border-color)',
            background: 'var(--bg-secondary)',
          }}
        >
          <ConceptDetailPanel
            apiUrl={apiUrl}
            token={token}
            topicId={topicId}
            conceptSlug={selectedNode.id}
            conceptTitle={selectedNode.title}
            onClose={() => setSelectedNode(null)}
            onConceptDeepened={fetchGraph}
          />
        </div>
      )}
    </div>
  );
};

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

  useEffect(() => {
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
      .force('collide', d3.forceCollide().radius(40));

    const link = svg
      .append('g')
      .attr('class', 'links')
      .selectAll('line')
      .data(links)
      .enter()
      .append('line')
      .attr('class', 'link')
      .attr('marker-end', 'url(#arrowhead)');

    const node = svg
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

    node.append('circle').attr('r', 15).attr('fill', '#4f46e5');

    node
      .append('text')
      .attr('dy', 25)
      .attr('text-anchor', 'middle')
      .text(d => d.title)
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

    return () => {
      simulation.stop();
    };
  }, [nodes, links]);

  if (isLoading) {
    return <div className="p-8 text-center text-gray-500">Loading knowledge graph...</div>;
  }

  if (error) {
    return <div className="p-8 text-center text-gray-500">{error}</div>;
  }

  return (
    <div className="flex h-[600px] border border-gray-200 rounded-lg overflow-hidden bg-gray-50">
      <div className="flex-1 relative" ref={containerRef}>
        <svg ref={svgRef} className="w-full h-full cursor-grab active:cursor-grabbing" />
        <div className="absolute top-4 left-4 bg-white p-3 rounded shadow text-sm border border-gray-100">
          <h3 className="font-semibold text-gray-700 mb-1">Knowledge Graph</h3>
          <p className="text-gray-500 text-xs">Drag nodes to explore. Click to read.</p>
        </div>
      </div>
      {selectedNode && (
        <div className="w-96 border-l border-gray-200 bg-white">
          <ConceptDetailPanel
            apiUrl={apiUrl}
            token={token}
            topicId={topicId}
            conceptSlug={selectedNode.id}
            conceptTitle={selectedNode.title}
            onClose={() => setSelectedNode(null)}
          />
        </div>
      )}
    </div>
  );
};

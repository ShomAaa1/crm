import { useState } from "react";
import type { CategoryTreeNode } from "@/types";

interface Props {
  nodes: CategoryTreeNode[];
  selectedId: string | null;
  onSelect: (id: string | null) => void;
}

export function CategoryTree({ nodes, selectedId, onSelect }: Props) {
  return (
    <div className="card p-3 space-y-1">
      <button
        onClick={() => onSelect(null)}
        className={`w-full text-left px-2 py-1 rounded text-sm ${
          selectedId === null
            ? "bg-brand-100 text-brand-800 font-medium"
            : "hover:bg-slate-100"
        }`}
      >
        Все категории
      </button>
      {nodes.map((n) => (
        <TreeNode key={n.id} node={n} selectedId={selectedId} onSelect={onSelect} />
      ))}
    </div>
  );
}

function TreeNode({
  node,
  selectedId,
  onSelect,
  depth = 0,
}: {
  node: CategoryTreeNode;
  selectedId: string | null;
  onSelect: (id: string) => void;
  depth?: number;
}) {
  const [open, setOpen] = useState(true);
  const hasChildren = node.children.length > 0;
  const isSelected = selectedId === node.id;

  return (
    <div>
      <div
        className={`flex items-center gap-1 px-2 py-1 rounded text-sm ${
          isSelected ? "bg-brand-100 text-brand-800 font-medium" : "hover:bg-slate-100"
        }`}
        style={{ paddingLeft: 8 + depth * 12 }}
      >
        {hasChildren ? (
          <button
            onClick={(e) => {
              e.stopPropagation();
              setOpen((v) => !v);
            }}
            className="w-4 text-slate-500 hover:text-slate-800"
          >
            {open ? "▾" : "▸"}
          </button>
        ) : (
          <span className="w-4" />
        )}
        <button onClick={() => onSelect(node.id)} className="flex-1 text-left">
          {node.name}
        </button>
      </div>
      {hasChildren && open && (
        <div>
          {node.children.map((c) => (
            <TreeNode
              key={c.id}
              node={c}
              selectedId={selectedId}
              onSelect={onSelect}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}

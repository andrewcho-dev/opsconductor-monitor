import { useState } from "react";
import {
  FolderOpen,
  Plus,
  Pencil,
  Trash2,
  ChevronDown,
  ChevronRight,
  Server,
} from "lucide-react";
import { cn } from "../lib/utils";

export function Sidebar({
  groups,
  selectedGroup,
  onSelectGroup,
  onCreateGroup,
  onEditGroup,
  onDeleteGroup,
  expandedSections,
  toggleSection,
}) {

  const handleSelectAll = () => {
    onSelectGroup({ type: "all", name: "All Devices" });
  };

  return (
    <div className="w-72 bg-white border-r border-gray-200 flex flex-col h-full">
      <div className="p-4 border-b border-gray-200">
        <h1 className="text-xl font-bold text-gray-800 flex items-center gap-2">
          <Server className="w-6 h-6 text-blue-600" />
          Network Monitor
        </h1>
      </div>

      <div className="flex-1 overflow-y-auto p-2">
        {/* All Devices */}
        <button
          onClick={() => {
                handleSelectAll();
          }}
          className={cn(
            "w-full flex items-center gap-2 px-3 py-2 rounded-lg text-left transition-colors",
            selectedGroup?.type === "all"
              ? "bg-blue-100 text-blue-700"
              : "hover:bg-gray-100 text-gray-700"
          )}
        >
          <Server className="w-4 h-4" />
          <span className="font-medium">All Devices</span>
        </button>

        {/* Custom Groups */}
        <div className="mt-4">
          <button
            onClick={() => toggleSection('custom')}
            className="flex items-center justify-between px-3 py-2 w-full hover:bg-gray-100 rounded-lg transition-colors"
          >
            <div className="flex items-center gap-2 text-sm font-semibold text-gray-500 uppercase tracking-wider">
              {expandedSections.custom ? (
                <ChevronDown className="w-4 h-4" />
              ) : (
                <ChevronRight className="w-4 h-4" />
              )}
              <FolderOpen className="w-4 h-4" />
              Custom Groups
            </div>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onCreateGroup();
              }}
              className="p-1 rounded hover:bg-gray-200 text-gray-500 hover:text-gray-700"
              title="Create new group"
            >
              <Plus className="w-4 h-4" />
            </button>
          </button>

          {expandedSections.custom && (
            <div className="ml-2 space-y-1">
              {groups.custom.map((group) => (
                <GroupItem
                  key={group.id}
                  group={{ ...group, type: "custom" }}
                  isSelected={
                    selectedGroup?.type === "custom" &&
                    selectedGroup?.id === group.id
                  }
                  onSelect={() =>
                    onSelectGroup({ type: "custom", id: group.id, name: group.group_name, data: group })
                  }
                  onEdit={() => onEditGroup({ type: "custom", ...group })}
                  onDelete={() => onDeleteGroup({ type: "custom", id: group.id })}
                  showActions={true}
                />
              ))}
              {groups.custom.length === 0 && (
                <p className="px-3 py-2 text-sm text-gray-400 italic">
                  No custom groups yet
                </p>
              )}
            </div>
          )}

        {/* Network Groups */}
        <div className="mt-4">
          <button
            onClick={() => toggleSection('network')}
            className="flex items-center justify-between px-3 py-2 w-full hover:bg-gray-100 rounded-lg transition-colors"
          >
            <div className="flex items-center gap-2 text-sm font-semibold text-gray-500 uppercase tracking-wider">
              {expandedSections.network ? (
                <ChevronDown className="w-4 h-4" />
              ) : (
                <ChevronRight className="w-4 h-4" />
              )}
              <FolderOpen className="w-4 h-4" />
              Network Groups
            </div>
          </button>

          {expandedSections.network && (
            <div className="ml-2 space-y-1">
              {groups.network.map((group) => (
                <GroupItem
                  key={group.network_range}
                  group={{ ...group, type: "network" }}
                  isSelected={
                    selectedGroup?.type === "network" &&
                    selectedGroup?.name === group.network_range
                  }
                  onSelect={() =>
                    onSelectGroup({ type: "network", name: group.network_range, data: group })
                  }
                  onEdit={() => {}} // Network groups can't be edited
                  onDelete={() => {}} // Network groups can't be deleted
                  showActions={false}
                />
              ))}
              {groups.network.length === 0 && (
                <p className="px-3 py-2 text-sm text-gray-400 italic">
                  No network groups found
                </p>
              )}
            </div>
          )}
        </div>
        </div>
      </div>
    </div>
  );
}

function GroupItem({ group, isSelected, onSelect, onEdit, onDelete, showActions }) {
  return (
    <div
      className={cn(
        "group flex items-center justify-between px-3 py-2 rounded-lg cursor-pointer transition-colors",
        isSelected ? "bg-blue-100 text-blue-700" : "hover:bg-gray-100 text-gray-700"
      )}
      onClick={() => {
        onSelect();
      }}
    >
      <div className="flex items-center gap-2 truncate flex-1">
        <span className="truncate text-sm">{group.name || group.group_name || group.network_range}</span>
        <span className="text-xs text-gray-500 font-medium">({group.device_count || 0})</span>
      </div>
      {showActions && (
        <div className="hidden group-hover:flex items-center gap-1 flex-shrink-0">
          <button
            onClick={(e) => {
              e.stopPropagation();
              onEdit();
            }}
            className="p-1 rounded hover:bg-gray-200"
          >
            <Pencil className="w-3 h-3" />
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDelete();
            }}
            className="p-1 rounded hover:bg-red-100 text-red-600"
          >
            <Trash2 className="w-3 h-3" />
          </button>
        </div>
      )}
    </div>
  );
}

import { useState, useEffect, useMemo } from "react";
import { Filter, X, ChevronDown, Check } from "lucide-react";
import { getFilters } from "../services/api";

export default function FilterPanel({ onFiltersChange }) {
  const [filters, setFilters] = useState({ categories: [], tags: [], documents: [] });
  const [selectedCategories, setSelectedCategories] = useState([]);
  const [selectedTags, setSelectedTags] = useState([]);
  const [selectedDocuments, setSelectedDocuments] = useState([]);
  const [expanded, setExpanded] = useState(null); // 'categories' | 'tags' | 'documents' | null
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getFilters()
      .then((res) => {
        const data = res.data;
        setFilters({
          categories: data.categories || [],
          tags: data.tags || [],
          documents: data.documents || [],
        });
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const hasActiveFilters = selectedCategories.length > 0 || selectedTags.length > 0 || selectedDocuments.length > 0;

  // Toggle a value in a selection array
  const toggleSelection = (setter, value) => {
    setter((prev) =>
      prev.includes(value) ? prev.filter((v) => v !== value) : [...prev, value]
    );
  };

  // When any selection changes, notify parent
  useEffect(() => {
    onFiltersChange?.({
      filter_categories: selectedCategories.length > 0 ? selectedCategories : undefined,
      filter_tags: selectedTags.length > 0 ? selectedTags : undefined,
      filter_document_ids: selectedDocuments.length > 0 ? selectedDocuments : undefined,
      hasFilters: hasActiveFilters,
    });
  }, [selectedCategories, selectedTags, selectedDocuments]);

  const clearFilters = () => {
    setSelectedCategories([]);
    setSelectedTags([]);
    setSelectedDocuments([]);
  };

  // Get documents for the expanded section
  const categoryCount = filters.categories.length;
  const tagCount = filters.tags.length;
  const docCount = filters.documents.length;

  return (
    <div className="border-b border-[#E5E7EB] bg-white">
      <div className="max-w-4xl mx-auto px-6 py-2">
        <div className="flex items-center gap-2">
          <Filter className="w-3.5 h-3.5 text-[#6B7280]" />
          <span className="text-xs font-medium text-[#6B7280] mr-1">Filters</span>

          {/* Category Selector */}
          <div className="relative">
            <button
              onClick={() => setExpanded(expanded === "categories" ? null : "categories")}
              className={`flex items-center gap-1 px-2.5 py-1.5 text-xs rounded-lg border transition-colors ${
                selectedCategories.length > 0
                  ? "border-[#2563EB] bg-[#EFF6FF] text-[#2563EB]"
                  : "border-[#E5E7EB] text-[#6B7280] hover:border-[#D1D5DB]"
              }`}
            >
              Category{selectedCategories.length > 0 && ` (${selectedCategories.length})`}
              {categoryCount > 0 && <ChevronDown className="w-3 h-3" />}
            </button>
            {expanded === "categories" && categoryCount > 0 && (
              <div className="absolute top-full left-0 mt-1 w-48 bg-white border border-[#E5E7EB] rounded-lg shadow-lg z-10 py-1 max-h-48 overflow-y-auto">
                {filters.categories.map((cat) => (
                  <button
                    key={cat}
                    onClick={() => toggleSelection(setSelectedCategories, cat)}
                    className="w-full flex items-center gap-2 px-3 py-1.5 text-xs text-[#374151] hover:bg-gray-50 text-left"
                  >
                    <div className={`w-3.5 h-3.5 rounded border flex items-center justify-center ${
                      selectedCategories.includes(cat)
                        ? "bg-[#2563EB] border-[#2563EB]"
                        : "border-[#D1D5DB]"
                    }`}>
                      {selectedCategories.includes(cat) && <Check className="w-2.5 h-2.5 text-white" />}
                    </div>
                    {cat}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Tags Selector */}
          {tagCount > 0 && (
            <div className="relative">
              <button
                onClick={() => setExpanded(expanded === "tags" ? null : "tags")}
                className={`flex items-center gap-1 px-2.5 py-1.5 text-xs rounded-lg border transition-colors ${
                  selectedTags.length > 0
                    ? "border-[#2563EB] bg-[#EFF6FF] text-[#2563EB]"
                    : "border-[#E5E7EB] text-[#6B7280] hover:border-[#D1D5DB]"
                }`}
              >
                Tags{selectedTags.length > 0 && ` (${selectedTags.length})`}
                <ChevronDown className="w-3 h-3" />
              </button>
              {expanded === "tags" && (
                <div className="absolute top-full left-0 mt-1 w-48 bg-white border border-[#E5E7EB] rounded-lg shadow-lg z-10 py-1 max-h-48 overflow-y-auto">
                  {filters.tags.map((tag) => (
                    <button
                      key={tag}
                      onClick={() => toggleSelection(setSelectedTags, tag)}
                      className="w-full flex items-center gap-2 px-3 py-1.5 text-xs text-[#374151] hover:bg-gray-50 text-left"
                    >
                      <div className={`w-3.5 h-3.5 rounded border flex items-center justify-center ${
                        selectedTags.includes(tag)
                          ? "bg-[#2563EB] border-[#2563EB]"
                          : "border-[#D1D5DB]"
                      }`}>
                        {selectedTags.includes(tag) && <Check className="w-2.5 h-2.5 text-white" />}
                      </div>
                      {tag}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Documents Selector */}
          {docCount > 0 && (
            <div className="relative">
              <button
                onClick={() => setExpanded(expanded === "documents" ? null : "documents")}
                className={`flex items-center gap-1 px-2.5 py-1.5 text-xs rounded-lg border transition-colors ${
                  selectedDocuments.length > 0
                    ? "border-[#2563EB] bg-[#EFF6FF] text-[#2563EB]"
                    : "border-[#E5E7EB] text-[#6B7280] hover:border-[#D1D5DB]"
                }`}
              >
                Documents{selectedDocuments.length > 0 && ` (${selectedDocuments.length})`}
                <ChevronDown className="w-3 h-3" />
              </button>
              {expanded === "documents" && (
                <div className="absolute top-full left-0 mt-1 w-56 bg-white border border-[#E5E7EB] rounded-lg shadow-lg z-10 py-1 max-h-56 overflow-y-auto">
                  {filters.documents.map((doc) => {
                    const displayName = doc.original_filename || doc.filename || "Untitled";
                    return (
                      <button
                        key={doc.document_id}
                        onClick={() => toggleSelection(setSelectedDocuments, doc.document_id)}
                        className="w-full flex items-center gap-2 px-3 py-1.5 text-xs text-[#374151] hover:bg-gray-50 text-left"
                      >
                        <div className={`w-3.5 h-3.5 rounded border flex items-center justify-center shrink-0 ${
                          selectedDocuments.includes(doc.document_id)
                            ? "bg-[#2563EB] border-[#2563EB]"
                            : "border-[#D1D5DB]"
                        }`}>
                          {selectedDocuments.includes(doc.document_id) && <Check className="w-2.5 h-2.5 text-white" />}
                        </div>
                        <span className="truncate">{displayName}</span>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* Clear Filters */}
          {hasActiveFilters && (
            <button
              onClick={clearFilters}
              className="flex items-center gap-1 px-2 py-1.5 text-xs text-[#6B7280] hover:text-red-500 transition-colors"
            >
              <X className="w-3 h-3" />
              Clear
            </button>
          )}

          {!hasActiveFilters && !loading && (
            <span className="text-xs text-[#9CA3AF]">All documents</span>
          )}
        </div>
      </div>
    </div>
  );
}

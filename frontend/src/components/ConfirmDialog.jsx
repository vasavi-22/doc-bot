import { AlertTriangle, X } from "lucide-react";

export default function ConfirmDialog({
  open,
  title = "Confirm",
  message = "Are you sure?",
  confirmLabel = "Delete",
  cancelLabel = "Cancel",
  onConfirm,
  onCancel,
  variant = "danger",
}) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl shadow-xl w-[400px] p-6 mx-4">
        <div className="flex items-start gap-4">
          <div
            className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 ${
              variant === "danger"
                ? "bg-red-100 text-red-600"
                : "bg-blue-100 text-blue-600"
            }`}
          >
            <AlertTriangle className="w-5 h-5" />
          </div>
          <div className="flex-1">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-base font-semibold text-[#111827]">
                {title}
              </h3>
              <button
                onClick={onCancel}
                className="p-0.5 rounded hover:bg-gray-100 transition-colors"
              >
                <X className="w-4 h-4 text-[#6B7280]" />
              </button>
            </div>
            <p className="text-sm text-[#6B7280]">{message}</p>
          </div>
        </div>
        <div className="flex justify-end gap-3 mt-6">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-sm font-medium text-[#374151] border border-[#E5E7EB] rounded-lg hover:bg-gray-50 transition-colors"
          >
            {cancelLabel}
          </button>
          <button
            onClick={onConfirm}
            className={`px-4 py-2 text-sm font-medium text-white rounded-lg transition-colors ${
              variant === "danger"
                ? "bg-red-600 hover:bg-red-700"
                : "bg-[#2563EB] hover:bg-blue-700"
            }`}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

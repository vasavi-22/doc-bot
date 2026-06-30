import { useState, useEffect } from "react";
import { Shield, Trash2, Search, AlertTriangle, User as UserIcon } from "lucide-react";
import { getUsers, updateUserRole, deleteUser } from "../services/api";
import { useToast } from "./Toast";
import ConfirmDialog from "./ConfirmDialog";

export default function Users() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [deleteTarget, setDeleteTarget] = useState(null);
  const { addToast } = useToast();

  const fetchUsers = async () => {
    try {
      const res = await getUsers();
      setUsers(res.data.users || []);
    } catch (err) {
      addToast(err.response?.data?.error || "Failed to load users", "error");
      setUsers([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const handleRoleChange = async (userId, newRole) => {
    try {
      await updateUserRole(userId, newRole);
      addToast(`User role updated to ${newRole}`, "success");
      fetchUsers();
    } catch (err) {
      addToast(err.response?.data?.error || "Failed to update role", "error");
    }
  };

  const confirmDelete = async () => {
    if (!deleteTarget) return;
    try {
      await deleteUser(deleteTarget.id);
      addToast(`User ${deleteTarget.name} deleted`, "success");
      fetchUsers();
    } catch (err) {
      addToast(err.response?.data?.error || "Failed to delete user", "error");
    }
    setDeleteTarget(null);
  };

  const filteredUsers = users.filter((u) =>
    `${u.name} ${u.email}`.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (loading) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <h1 className="text-[32px] font-bold text-[#111827] mb-6">Users</h1>
        <div className="flex items-center justify-center py-20">
          <div className="w-6 h-6 border-2 border-[#2563EB] border-t-transparent rounded-full animate-spin" />
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-[32px] font-bold text-[#111827]">Users</h1>
        <p className="text-[#6B7280] mt-1">Manage user accounts and roles.</p>
      </div>

      {/* Search Bar */}
      <div className="relative mb-6">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#9CA3AF]" />
        <input
          type="text"
          placeholder="Search users by name or email..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full h-10 pl-10 pr-4 text-sm border border-[#E5E7EB] rounded-lg outline-none focus:border-[#2563EB] focus:ring-1 focus:ring-[#2563EB] transition-colors"
        />
      </div>

      {/* Users Table */}
      <div className="rounded-xl border border-[#E5E7EB] bg-white shadow-sm overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-[#E5E7EB] bg-gray-50">
              <th className="text-left text-xs font-medium text-[#9CA3AF] px-6 py-4">User</th>
              <th className="text-left text-xs font-medium text-[#9CA3AF] px-6 py-4">Email</th>
              <th className="text-left text-xs font-medium text-[#9CA3AF] px-6 py-4">Role</th>
              <th className="text-left text-xs font-medium text-[#9CA3AF] px-6 py-4">Joined</th>
              <th className="text-right text-xs font-medium text-[#9CA3AF] px-6 py-4">Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredUsers.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-6 py-12 text-center text-sm text-[#9CA3AF]">
                  {searchQuery ? "No users match your search." : "No users found."}
                </td>
              </tr>
            ) : (
              filteredUsers.map((u) => (
                <tr
                  key={u.id}
                  className="border-b border-[#E5E7EB] last:border-b-0 hover:bg-gray-50 transition-colors"
                >
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 bg-[#2563EB] rounded-full flex items-center justify-center text-white text-sm font-medium">
                        {u.name
                          ? u.name.split(" ").map((n) => n[0]).join("").toUpperCase().slice(0, 2)
                          : "U"}
                      </div>
                      <span className="text-sm font-medium text-[#111827]">{u.name}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-sm text-[#6B7280]">{u.email}</td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <select
                        value={u.role}
                        onChange={(e) => handleRoleChange(u.id, e.target.value)}
                        className={`text-xs font-medium px-2.5 py-1 rounded-full border transition-colors cursor-pointer focus:outline-none focus:ring-1 focus:ring-[#2563EB] ${
                          u.role === "admin"
                            ? "bg-[#FEF3C7] text-[#D97706] border-[#FDE68A]"
                            : "bg-[#F3F4F6] text-[#6B7280] border-[#E5E7EB]"
                        }`}
                      >
                        <option value="employee">Employee</option>
                        <option value="admin">Admin</option>
                      </select>
                      {u.role === "admin" && (
                        <Shield className="w-3 h-3 text-[#D97706]" />
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4 text-sm text-[#6B7280]">
                    {u.created_at ? new Date(u.created_at).toLocaleDateString() : "Unknown"}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <button
                      onClick={() => setDeleteTarget(u)}
                      className="p-1.5 rounded-lg hover:bg-red-50 transition-colors"
                      title="Delete user"
                    >
                      <Trash2 className="w-4 h-4 text-red-500" />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Info Box */}
      <div className="mt-6 p-4 bg-[#F5F9FF] rounded-xl border border-[#BFDBFE]">
        <div className="flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-[#2563EB] shrink-0 mt-0.5" />
          <div className="text-sm text-[#374151]">
            <p className="font-medium mb-1">Role Management</p>
            <p>
              <strong>Admin</strong> — Full access: can upload documents, manage users, view all documents, and delete content.
            </p>
            <p className="mt-1">
              <strong>Employee</strong> — Basic access: can chat, upload personal documents, and view permitted content only.
            </p>
          </div>
        </div>
      </div>

      {/* Delete Confirmation */}
      <ConfirmDialog
        open={!!deleteTarget}
        title="Delete User"
        message={`Are you sure you want to delete "${(deleteTarget?.name || "")}"? This will permanently remove the user and all their data (documents, chats, messages).`}
        confirmLabel="Delete"
        cancelLabel="Cancel"
        onConfirm={confirmDelete}
        onCancel={() => setDeleteTarget(null)}
        variant="danger"
      />
    </div>
  );
}

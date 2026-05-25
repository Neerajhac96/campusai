import { useAuth } from "../context/AuthContext";

const Navbar = ({ title, subtitle }) => {
  const { user, logout } = useAuth();

  return (
    <header className="border-b border-gray-200 bg-white px-4 py-3 shadow-sm">
      <div className="mx-auto flex max-w-7xl items-center justify-between">
        <div>
          <h1 className="text-lg font-bold text-wa-dark">{title}</h1>
          {subtitle ? <p className="text-sm text-gray-500">{subtitle}</p> : null}
        </div>
        <div className="flex items-center gap-3">
          <div className="text-right">
            <p className="text-sm font-semibold text-gray-800">{user?.name}</p>
            <p className="text-xs text-gray-500">{user?.email}</p>
          </div>
          <button
            type="button"
            onClick={logout}
            className="rounded-md bg-wa-dark px-3 py-2 text-sm font-semibold text-white hover:bg-[#05453e]"
          >
            Logout
          </button>
        </div>
      </div>
    </header>
  );
};

export default Navbar;

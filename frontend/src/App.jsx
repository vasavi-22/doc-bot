import Header from "./components/Header";
import ChatBox from "./components/ChatBox";
import FileUpload from "./components/FileUpload";

export default function App() {
  return (
    <div className="h-screen flex flex-col bg-[#020617]">
      
      {/* Header */}
      <Header />

      {/* Upload */}
      <FileUpload />

      {/* Chat */}
      <div className="flex-1 overflow-hidden">
        <ChatBox />
      </div>
    </div>
  );
}
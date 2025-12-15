import { Navbar } from "@/components/ui/mini-navbar";
import { FileUpload } from "@/components/ui/file-upload";
import { WavyBackground } from "@/components/ui/wavy_background";
import React from "react";

export default function ChatPage() {
  return (
    <WavyBackground>
      <Navbar />
      <main className="flex-1 flex items-center justify-center">
        <div className="w-full max-w-2xl mx-auto">
          <FileUpload />
        </div>
      </main>
    </WavyBackground>
  );
} 
"use client";
import { Navbar } from "@/components/ui/mini-navbar";
import { LampContainer } from "@/components/ui/lamp";
import React from "react";

export default function SettingsPage() {
  return (
    <>
      <Navbar />
      <LampContainer>
        <div className="flex flex-1 w-full h-full items-center justify-center min-h-[40vh]">
          <h1 className="text-5xl md:text-7xl font-bold bg-gradient-to-br from-cyan-400 via-white to-cyan-600 bg-clip-text text-transparent text-center drop-shadow-lg animate-fade-in">
            Coming Soon
          </h1>
        </div>
      </LampContainer>
    </>
  );
} 
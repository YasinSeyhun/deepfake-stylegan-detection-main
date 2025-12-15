'use client';
// -- coding: utf-8 --
import React, { useEffect, useState } from "react";

interface TemplateSelectorProps {
  onSelect: (templateName: string) => void;
}

export default function TemplateSelector({ onSelect }: TemplateSelectorProps) {
  const [templates, setTemplates] = useState<{ name: string; displayName: string }[]>([]);
  useEffect(() => {
    fetch("/mail_templates/")
      .then(res => res.json())
      .then(setTemplates);
  }, []);
  return (
    <select onChange={e => onSelect(e.target.value)} className="p-4 rounded-2xl shadow">
      <option value="">Şablon Seç</option>
      {templates.map(t => (
        <option key={t.name} value={t.name}>{t.displayName}</option>
      ))}
    </select>
  );
} 
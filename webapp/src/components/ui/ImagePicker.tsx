'use client';
// -- coding: utf-8 --
import React, { useEffect, useState } from "react";

interface ImagePickerProps {
  selected: string | null;
  onSelect: (img: string) => void;
}

export default function ImagePicker({ selected, onSelect }: ImagePickerProps) {
  const [images, setImages] = useState<string[]>([]);
  useEffect(() => {
    fetch("/fake_faces/")
      .then(res => res.json())
      .then(setImages);
  }, []);
  return (
    <div className="grid grid-cols-4 gap-4">
      {images.map(img => (
        <img
          key={img}
          src={`/fake_faces/${img}`}
          alt={img}
          className={`rounded-2xl shadow cursor-pointer border-4 ${selected === img ? "border-blue-500" : "border-transparent"}`}
          onClick={() => onSelect(img)}
        />
      ))}
    </div>
  );
} 
"use client";
import Hero from "@/components/Hero";
// removed unused Logos import
import Features from "@/components/Features";
// removed unused Showcase import
import Pricing from "@/components/Pricing";
import FAQ from "@/components/FAQ";
import Footer from "@/components/Footer";

export default function Home() {
  

  return (
    <main className="">
      <Hero />
      <Features />
      {/* <Showcase /> */}
      <Pricing />
      <FAQ />
      <Footer />
    </main>
  );
}

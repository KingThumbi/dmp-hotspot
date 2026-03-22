import Hero from "../../components/sections/Hero";
import StatsCounter from "../../components/sections/StatsCounter";
import PackagesPreview from "../../components/sections/PackagesPreview";
import Services from "../../components/sections/Services";
import TestimonialsStrip from "../../components/sections/TestimonialsStrip";
import CoveragePreview from "../../components/sections/CoveragePreview";

export default function Home() {
  return (
    <>
      <Hero />
      <StatsCounter />
      <PackagesPreview />
      <Services />
      <TestimonialsStrip />
      <CoveragePreview />
    </>
  );
}

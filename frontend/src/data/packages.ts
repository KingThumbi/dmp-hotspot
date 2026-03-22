export type ResidentialPackage = {
  code: string;
  speedMbps: number;
  priceKes: number;
  perks: string[];
};

export type HotspotPackage = {
  code: string;
  users: number;
  duration: "Daily" | "Weekly" | "Monthly";
  priceKes: number;
  perks: string[];
};

export const residentialPackages: ResidentialPackage[] = [
  { code: "R-3",  speedMbps: 3,  priceKes: 1000, perks: ["Unlimited browsing", "Reliable speeds", "Support included"] },
  { code: "R-7",  speedMbps: 7,  priceKes: 1500, perks: ["Streaming ready", "Stable connection", "Support included"] },
  { code: "R-12", speedMbps: 12, priceKes: 2000, perks: ["Fast downloads", "Work-from-home ready", "Support included"] },
  { code: "R-20", speedMbps: 20, priceKes: 2500, perks: ["4K streaming", "Multiple devices", "Priority support"] },
  { code: "R-30", speedMbps: 30, priceKes: 3000, perks: ["Heavy usage", "Best value speed tier", "Priority support"] },
];

export const hotspotPackages: HotspotPackage[] = [
  { code: "H-1D-1", users: 1, duration: "Daily",   priceKes: 50,  perks: ["Instant access", "Good for quick use"] },
  { code: "H-1W-1", users: 1, duration: "Weekly",  priceKes: 100, perks: ["Weekly bundle", "Stable access"] },
  { code: "H-1M-1", users: 1, duration: "Monthly", priceKes: 300, perks: ["Best for individuals", "Monthly access"] },

  { code: "H-2D-2", users: 2, duration: "Daily",   priceKes: 80,  perks: ["2 users", "Great for couples"] },
  { code: "H-2W-2", users: 2, duration: "Weekly",  priceKes: 160, perks: ["2 users", "Weekly bundle"] },
  { code: "H-2M-2", users: 2, duration: "Monthly", priceKes: 500, perks: ["2 users", "Monthly bundle"] },

  { code: "H-5D-5", users: 5, duration: "Daily",   priceKes: 100, perks: ["Small group", "Day access"] },
  { code: "H-5W-5", users: 5, duration: "Weekly",  priceKes: 300, perks: ["Small group", "Week access"] },
  { code: "H-5M-5", users: 5, duration: "Monthly", priceKes: 900, perks: ["Small group", "Month access"] },
];

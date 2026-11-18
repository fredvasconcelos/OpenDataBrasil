import next from "eslint-config-next/core-web-vitals";
import ts from "eslint-config-next/typescript";

const config = [
  ...next,
  ...ts,
  { ignores: [".next/**", "node_modules/**", "src/lib/api-schema.ts", "next-env.d.ts"] },
];

export default config;

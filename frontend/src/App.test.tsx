import { describe, it, expect } from "vitest";
import { renderToString } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import App from "./App";
describe("product views", () => {
  for (const [route, content] of [
    ["/", "Production broke."],
    ["/control", "Mission control"],
    ["/architecture", "Built to show its work."],
    ["/intelligence", "Incident intelligence"],
    ["/evaluations", "Evaluation arena"],
  ]) {
    it("renders " + route + " without fabricated records", () => {
      const html = renderToString(
        <MemoryRouter initialEntries={[route]}>
          <App />
        </MemoryRouter>,
      );
      expect(html).toContain(content);
      expect(html).not.toContain("NaN");
    });
  }
});

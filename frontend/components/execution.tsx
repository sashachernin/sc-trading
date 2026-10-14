import { Panel } from "./ui";
export type PaperFill = {
  id: string;
  ticker: string;
  quantity: string;
  price: string;
  fee: string;
  side: string;
  observation_time: string;
  fill_time: string;
  provider: string;
  label: string;
};
export default function Execution({ fills }: { fills: PaperFill[] }) {
  if (!fills.length) return null;
  return (
    <Panel title="Trades">
      {fills.length ? (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Side</th>
                <th>Shares</th>
                <th>Price</th>

                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              {fills.map((f) => (
                <tr key={f.id}>
                  <td>{f.ticker}</td>
                  <td>{f.side === "BUY" ? "Bought" : "Sold"}</td>
                  <td>{Number(f.quantity).toFixed(4)}</td>
                  <td>{Number(f.price).toFixed(2)}</td>

                  <td>
                    {new Date(f.fill_time).toLocaleString("en-US", {
                      timeZone: "America/New_York",
                      month: "short",
                      day: "numeric",
                      hour: "numeric",
                      minute: "2-digit",
                    })}{" "}
                    ET
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </Panel>
  );
}

// R6.2 case `jsx`: JSX elements in a `.tsx` file. Answers 128 Q3 — JSX needs no new vocabulary; a
// JSX element is not a call, so it emits no spurious edge, while `this.method()` inside JSX still
// resolves.
import { View } from "./ui";

export function App(): JSX.Element {
  return <View className="root">hello</View>;
}

export class Panel {
  render(): JSX.Element {
    return <div>{this.title()}</div>;
  }

  title(): string {
    return "t";
  }
}

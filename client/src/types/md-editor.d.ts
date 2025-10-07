declare module "@uiw/react-md-editor" {
  import * as React from "react";
  type Props = {
    value?: string;
    onChange?: (val?: string) => void;
    height?: number;
  // Allow additional props without using any
    [key: string]: unknown;
  };
  const MDEditor: React.FC<Props>;
  export default MDEditor;
}

declare module "@uiw/react-markdown-preview" {
  import * as React from "react";
  type Props = { source?: string; [key: string]: unknown };
  const MarkdownPreview: React.FC<Props>;
  export default MarkdownPreview;
}

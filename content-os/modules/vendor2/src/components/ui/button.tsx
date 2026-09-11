import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/content-os/cn";
import type { ButtonHTMLAttributes } from "react";

const buttonVariants = cva(
  "inline-flex min-h-11 items-center justify-center gap-2 rounded-sm px-4 text-sm font-medium transition-opacity duration-150 disabled:pointer-events-none disabled:opacity-40",
  {
    variants: {
      variant: {
        primary: "bg-steel text-steel-fg hover:opacity-90",
        secondary: "bg-raised text-ink hover:opacity-90",
        ghost: "bg-transparent text-ink hover:bg-raised",
        danger: "bg-danger text-paper hover:opacity-90",
      },
    },
    defaultVariants: { variant: "primary" },
  },
);

export function Button({
  className,
  variant,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & VariantProps<typeof buttonVariants>) {
  return <button className={cn(buttonVariants({ variant }), className)} {...props} />;
}

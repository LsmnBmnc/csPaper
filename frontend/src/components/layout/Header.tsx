import React from "react";

export function Header() {
  return (
    <header className="header">
      <div className="header-left">
        <div className="logo-mark" />
        <span className="logo-text">csPaper Review</span>
      </div>

      <nav className="header-nav">
        <a className="nav-link" href="#">
          Products
        </a>
        <a className="nav-link" href="#">
          Help
        </a>
      </nav>

      <div className="header-right">
        <div className="user-avatar">G</div>
        <span className="user-name">Guest</span>
      </div>
    </header>
  );
}
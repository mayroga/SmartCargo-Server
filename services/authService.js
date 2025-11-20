import jwt from "jsonwebtoken";

export const authService = {
  login: async ({ username }) => {
    const token = jwt.sign({ username }, process.env.JWT_SECRET, { expiresIn: "12h" });
    return token;
  }
};

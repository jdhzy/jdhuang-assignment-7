from flask import Flask, render_template, request, url_for, session
import numpy as np
import matplotlib
from flask_session import Session

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression

app = Flask(__name__)
app.secret_key = "your_secret_key_here"  # Replace with your own secret key, needed for session management
app.config['SESSION_TYPE'] = 'filesystem'  # Can use 'redis' or 'memcached' if set up
Session(app)

def generate_data(N, mu, beta0, beta1, sigma2, S):
    # Generate data and initial plots

    # 1: Generate a random dataset X of size N with values between 0 and 1
    X = np.random.uniform(0, 1, N)

    # 2: Generate a random dataset Y using the specified beta0, beta1, mu, and sigma2
    error = np.random.normal(loc=mu * X, scale=np.sqrt(sigma2), size=N)
    Y = beta0 + beta1 * X + error

    # Fit a linear regression model to X and Y
    model = LinearRegression()
    model.fit(X.reshape(-1, 1), Y)
    slope = model.coef_[0]  # Extract the slope
    intercept = model.intercept_  # Extract the intercept

    # Generate a scatter plot of (X, Y) with the fitted regression line
    plot1_path = "static/plot1.png"
    plt.figure()
    plt.scatter(X, Y, color='blue', label='Data points')
    plt.plot(X, model.predict(X.reshape(-1, 1)), color='red', label='Fitted line')
    plt.xlabel('X')
    plt.ylabel('Y')
    plt.title('Scatter Plot with Fitted Regression Line')
    plt.legend()
    plt.savefig(plot1_path)
    plt.close()

    # Run S simulations to generate slopes and intercepts
    slopes = []
    intercepts = []

    for _ in range(S):
        # Generate simulated datasets using the same beta0 and beta1
        X_sim = np.random.uniform(0, 1, N)
        error_sim = np.random.normal(loc=mu * X_sim, scale=np.sqrt(sigma2), size=N)
        Y_sim = beta0 + beta1 * X_sim + error_sim

        # Fit linear regression to simulated data and store slope and intercept
        sim_model = LinearRegression()
        sim_model.fit(X_sim.reshape(-1, 1), Y_sim)
        sim_slope = sim_model.coef_[0]
        sim_intercept = sim_model.intercept_

        slopes.append(sim_slope)
        intercepts.append(sim_intercept)

    # Plot histograms of slopes and intercepts
    plot2_path = "static/plot2.png"
    plt.figure()
    plt.hist(slopes, bins=30, color='skyblue', edgecolor='black')
    plt.title('Histogram of Simulated Slopes')
    plt.xlabel('Slope')
    plt.ylabel('Frequency')
    plt.savefig(plot2_path)
    plt.close()

    # Calculate proportions of slopes and intercepts more extreme than observed
    slope_more_extreme = np.mean(np.abs(slopes) > np.abs(slope))
    intercept_extreme = np.mean(np.abs(intercepts) > np.abs(intercept))

    # Return data needed for further analysis
    return (
        X,
        Y,
        slope,
        intercept,
        plot1_path,
        plot2_path,
        slope_more_extreme,
        intercept_extreme,
        slopes,
        intercepts,
    )


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # Get user input from the form
        N = int(request.form["N"])
        mu = float(request.form["mu"])
        sigma2 = float(request.form["sigma2"])
        beta0 = float(request.form["beta0"])
        beta1 = float(request.form["beta1"])
        S = int(request.form["S"])

        # Generate data and initial plots
        (
            X,
            Y,
            slope,
            intercept,
            plot1,
            plot2,
            slope_extreme,
            intercept_extreme,
            slopes,
            intercepts,
        ) = generate_data(N, mu, beta0, beta1, sigma2, S)

        # Store data in session
        session["X"] = X.tolist()
        session["Y"] = Y.tolist()
        session["slope"] = slope
        session["intercept"] = intercept
        session["slopes"] = slopes
        session["intercepts"] = intercepts
        session["slope_extreme"] = slope_extreme
        session["intercept_extreme"] = intercept_extreme
        session["N"] = N
        session["mu"] = mu
        session["sigma2"] = sigma2
        session["beta0"] = beta0
        session["beta1"] = beta1
        session["S"] = S

        print("N stored in session:", session.get("N"))
        print("Slope stored in session:", session.get("slope"))

        # Return render_template with variables
        return render_template(
            "index.html",
            plot1=plot1,
            plot2=plot2,
            slope_extreme=slope_extreme,
            intercept_extreme=intercept_extreme,
            N=N,
            mu=mu,
            sigma2=sigma2,
            beta0=beta0,
            beta1=beta1,
            S=S,
        )
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    # This route handles data generation (same as above)
    return index()


@app.route("/hypothesis_test", methods=["POST"])
def hypothesis_test():
    # Check if session variables are None
    # Debugging prints to check session data
    print("Session data - N:", session.get("N"))
    print("Session data - S:", session.get("S"))
    print("Session data - slope:", session.get("slope"))
    print("Session data - intercept:", session.get("intercept"))
    if session.get("N") is None or session.get("S") is None:
        return "Error: Missing session data for N or S", 400
    
    # Retrieve data from session
    N = int(session.get("N"))
    S = int(session.get("S"))
    slope = float(session.get("slope"))
    intercept = float(session.get("intercept"))
    slopes = session.get("slopes")
    intercepts = session.get("intercepts")
    beta0 = float(session.get("beta0"))
    beta1 = float(session.get("beta1"))

    parameter = request.form.get("parameter")
    test_type = request.form.get("test_type")

    # Use the slopes or intercepts from the simulations
    if parameter == "slope":
        simulated_stats = np.array(slopes)
        observed_stat = slope
        hypothesized_value = beta1
    else:
        simulated_stats = np.array(intercepts)
        observed_stat = intercept
        hypothesized_value = beta0

    # 10: Calculate p-value based on test type
    if test_type == '>':
        p_value = np.mean(simulated_stats >= observed_stat)
    elif test_type == '<':
        p_value = np.mean(simulated_stats <= observed_stat)
    elif test_type == '!=':
        p_value = np.mean(np.abs(simulated_stats - hypothesized_value) >= np.abs(observed_stat - hypothesized_value))

    
    # 11: If p_value is very small (e.g., <= 0.0001), set fun_message to a fun message
    fun_message = "You have encountered a rare event!" if p_value <= 0.0001 else None

    # 12: Plot histogram of simulated statistics
    plot3_path = "static/plot3.png"
    # Replace with code to generate and save the plot
    plt.figure()
    plt.hist(simulated_stats, bins=30, color='skyblue', edgecolor='black')
    plt.axvline(observed_stat, color='red', linestyle='--', label='Observed Statistic')
    plt.axvline(hypothesized_value, color='green', linestyle='-', label='Hypothesized Value')
    plt.title('Histogram of Simulated Statistics')
    plt.xlabel('Statistic Value')
    plt.ylabel('Frequency')
    plt.legend()
    plt.savefig(plot3_path)
    plt.close()

    # Return results to template
    return render_template(
        "index.html",
        plot1="static/plot1.png",
        plot2="static/plot2.png",
        plot3=plot3_path,
        parameter=parameter,
        observed_stat=observed_stat,
        hypothesized_value=hypothesized_value,
        N=N,
        beta0=beta0,
        beta1=beta1,
        S=S,
        p_value=p_value,
        fun_message=fun_message,
    )

@app.route("/confidence_interval", methods=["POST"])
def confidence_interval():
    # Retrieve data from session
    N = int(session.get("N"))
    mu = float(session.get("mu"))
    sigma2 = float(session.get("sigma2"))
    beta0 = float(session.get("beta0"))
    beta1 = float(session.get("beta1"))
    S = int(session.get("S"))
    X = np.array(session.get("X"))
    Y = np.array(session.get("Y"))
    slope = float(session.get("slope"))
    intercept = float(session.get("intercept"))
    slopes = session.get("slopes")
    intercepts = session.get("intercepts")

    parameter = request.form.get("parameter")
    confidence_level = float(request.form.get("confidence_level"))

    # Use the slopes or intercepts from the simulations
    if parameter == "slope":
        estimates = np.array(slopes)
        observed_stat = slope
        true_param = beta1
    else:
        estimates = np.array(intercepts)
        observed_stat = intercept
        true_param = beta0

    # TODO 14: Calculate mean and standard deviation of the estimates
    mean_estimate = np.mean(estimates)
    std_estimate = np.std(estimates)

    # TODO 15: Calculate confidence interval for the parameter estimate
    # Use the t-distribution and confidence_level
    confidence_level = float(request.form.get("confidence_level")) / 100  # Convert to decimal

    ci_lower = np.percentile(estimates, (1 - confidence_level) / 2 * 100)
    ci_upper = np.percentile(estimates, (1 + confidence_level) / 2 * 100)

    # TODO 16: Check if confidence interval includes true parameter
    includes_true = ci_lower <= true_param <= ci_upper

    # TODO 17: Plot the individual estimates as gray points and confidence interval
    # Plot the mean estimate as a colored point which changes if the true parameter is included
    # Plot the confidence interval as a horizontal line
    # Plot the true parameter value
    plot4_path = "static/plot4.png"
    # Write code here to generate and save the plot
    plt.figure(figsize=(10, 6))
    plt.scatter(estimates, np.zeros_like(estimates), color='gray', alpha=0.5, label='Simulated Estimates')
    plt.axhline(0, color='black', linewidth=0.5)  # baseline for visual reference
    plt.axvline(mean_estimate, color='blue', linestyle='-', linewidth=2, label='Mean Estimate')
    plt.axvline(true_param, color='green', linestyle='--', linewidth=2, label='True Parameter')
    plt.hlines(0, ci_lower, ci_upper, color='blue', linewidth=2, label=f'{confidence_level*100}% CI')

    # Highlight the mean estimate as a big blue dot
    plt.scatter([mean_estimate], [0], color='blue', s=100, zorder=3)

    plt.title(f'{confidence_level*100}% Confidence Interval for {parameter.capitalize()} (Mean Estimate)')
    plt.xlabel(f'{parameter.capitalize()} Estimate')
    plt.yticks([])  # Remove y-ticks since it's not needed
    plt.legend()
    plt.savefig(plot4_path)
    plt.close()

    # Return results to template
    return render_template(
        "index.html",
        plot1="static/plot1.png",
        plot2="static/plot2.png",
        plot4=plot4_path,
        parameter=parameter,
        confidence_level=confidence_level,
        mean_estimate=mean_estimate,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        includes_true=includes_true,
        observed_stat=observed_stat,
        N=N,
        mu=mu,
        sigma2=sigma2,
        beta0=beta0,
        beta1=beta1,
        S=S,
    )


if __name__ == "__main__":
    app.run(debug=True)
